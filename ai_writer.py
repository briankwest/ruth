#!/usr/bin/env python3
"""
AI Writer for Senator Mullin
Complete system for generating AI-powered letters to Senator Markwayne Mullin
Analyzes news articles, drafts letters in Brian West's progressive voice,
and outputs JSON files for the mailer PDF generation system
"""

import os
import sys
import time
import json
import csv
import tempfile
import subprocess
import platform
import logging
import requests
import trafilatura
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from newspaper import Article
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_writer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ==================== NEWS ARTICLE FETCHER ====================

class NewsArticleFetcher:
    """Fetches and extracts content from news articles"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_article(self, url: str) -> Dict[str, str]:
        """Fetch and extract article content from a URL"""
        try:
            logger.info(f"Fetching article from: {url}")

            # Method 1: Try newspaper3k first
            try:
                article = Article(url)
                article.download()
                article.parse()

                if article.text:
                    return {
                        'url': url,
                        'title': article.title or 'Untitled',
                        'text': article.text,
                        'authors': ', '.join(article.authors) if article.authors else 'Unknown',
                        'publish_date': str(article.publish_date) if article.publish_date else 'Unknown',
                        'summary': article.summary if hasattr(article, 'summary') else '',
                        'source': self._extract_source(url)
                    }
            except:
                pass

            # Method 2: Fallback to trafilatura
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            extracted = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                deduplicate=True
            )

            if extracted:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title').text.strip() if soup.find('title') else 'Untitled'

                return {
                    'url': url,
                    'title': title,
                    'text': extracted,
                    'authors': 'Unknown',
                    'publish_date': 'Unknown',
                    'summary': extracted[:500] + '...' if len(extracted) > 500 else extracted,
                    'source': self._extract_source(url)
                }

            # Method 3: Basic HTML extraction
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()

            # Get text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            title = soup.find('title').text.strip() if soup.find('title') else 'Untitled'

            return {
                'url': url,
                'title': title,
                'text': text[:5000],  # Limit to first 5000 chars
                'authors': 'Unknown',
                'publish_date': 'Unknown',
                'summary': text[:500] + '...' if len(text) > 500 else text,
                'source': self._extract_source(url)
            }

        except Exception as e:
            logger.error(f"Error fetching article from {url}: {e}")
            return {
                'url': url,
                'title': 'Error fetching article',
                'text': f'Could not fetch article: {str(e)}',
                'authors': 'Unknown',
                'publish_date': 'Unknown',
                'summary': '',
                'source': self._extract_source(url)
            }

    def _extract_source(self, url: str) -> str:
        """Extract source domain from URL"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except:
            return 'Unknown'

    def fetch_multiple_articles(self, urls: List[str]) -> List[Dict[str, str]]:
        """Fetch multiple articles"""
        articles = []
        for url in urls:
            article = self.fetch_article(url)
            articles.append(article)
        return articles


# ==================== AI LETTER DRAFTER ====================

class AILetterDrafter:
    """Uses OpenAI to draft letters based on news context"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY in .env file")

        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')  # Default to GPT-4 Turbo
        logger.info(f"Using OpenAI model: {self.model}")

        # Load custom system prompt if available
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load custom system prompt from prompt.md if available"""
        prompt_file = 'prompt.md'
        default_prompt = """You are an expert constituent communications specialist who helps citizens write effective letters to their representatives. You write clear, compelling, and action-oriented letters that get results."""

        try:
            if os.path.exists(prompt_file):
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    custom_prompt = f.read()
                    if custom_prompt.strip():
                        logger.info(f"Loaded custom system prompt from {prompt_file}")
                        return custom_prompt
        except Exception as e:
            logger.warning(f"Could not load custom prompt: {e}")

        return default_prompt

    def analyze_articles(self, articles: List[Dict[str, str]]) -> str:
        """Analyze articles and extract key points"""
        try:
            # Prepare article summaries
            article_summaries = []
            for i, article in enumerate(articles, 1):
                summary = f"""
Article {i}: {article['title']}
Source: {article['source']}
Date: {article['publish_date']}
Key Content: {article['text'][:2000]}...
"""
                article_summaries.append(summary)

            prompt = f"""Analyze these news articles and extract the key policy issues, concerns, and actionable points relevant to a U.S. Senator:

{chr(10).join(article_summaries)}

Please provide:
1. Main issue(s) discussed
2. How this affects Oklahoma constituents
3. Specific policy implications
4. Recommended actions for the Senator
5. Key facts and statistics mentioned"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert policy analyst helping constituents communicate with their representatives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error analyzing articles: {e}")
            return f"Error analyzing articles: {str(e)}"

    def draft_letter(self,
                    articles: List[Dict[str, str]],
                    sender_info: Dict[str, str],
                    tone: str = "professional",
                    focus: Optional[str] = None,
                    additional_context: Optional[str] = None,
                    recipient: Optional[Dict] = None) -> Tuple[str, str]:
        """
        Draft a letter to an official based on news articles
        """
        try:
            # First, analyze the articles
            analysis = self.analyze_articles(articles)

            # Prepare the context
            article_summaries = []
            for article in articles:
                article_summaries.append(f"- {article['title']} ({article['source']})")

            context = f"""
News Articles Referenced:
{chr(10).join(article_summaries)}

Analysis:
{analysis}

Sender Information:
- Name: {sender_info.get('first_name', '')} {sender_info.get('last_name', '')}
- Location: {sender_info.get('city', '')}, {sender_info.get('state', 'OK')}

Tone: {tone}
Focus: {focus or 'General policy concern'}
Additional Context: {additional_context or 'None provided'}
"""

            # Check if using Brian West's custom prompt
            using_brian_prompt = "Brian West" in self.system_prompt

            # Get recipient info or default to Senator Mullin
            if recipient:
                recipient_name = recipient.get('name', 'Senator Mullin')
                recipient_title = recipient.get('title', 'Senator')
                office_type = recipient.get('office_type', 'federal_senate')

                # Customize salutation based on office type
                if office_type == 'governor':
                    salutation = f"Governor {recipient_name.split()[-1]}"
                    office_desc = "Governor of Oklahoma"
                    action_context = "state executive actions and policies"
                elif office_type == 'federal_senate':
                    salutation = f"Senator {recipient_name.split()[-1]}"
                    office_desc = "United States Senator"
                    action_context = "federal legislation and oversight"
                elif office_type == 'federal_house':
                    salutation = f"Representative {recipient_name.split()[-1]}"
                    office_desc = "United States Representative"
                    action_context = "federal legislation and district representation"
                elif office_type == 'state_senate':
                    salutation = f"Senator {recipient_name.split()[-1]}"
                    office_desc = "State Senator"
                    action_context = "state legislation and district concerns"
                elif office_type == 'state_house':
                    salutation = f"Representative {recipient_name.split()[-1]}"
                    office_desc = "State Representative"
                    action_context = "state legislation and local representation"
                else:
                    salutation = recipient_name
                    office_desc = recipient_title
                    action_context = "policy actions"
            else:
                # Default to Senator Mullin if no recipient specified
                recipient_name = "Markwayne Mullin"
                salutation = "Senator Mullin"
                office_desc = "United States Senator"
                action_context = "federal legislation and oversight"
                office_type = 'federal_senate'

            # Create the letter drafting prompt
            if using_brian_prompt:
                # When using Brian's prompt, the system already knows who he is
                letter_prompt = f"""Draft a letter to {recipient_title} {recipient_name} ({office_desc}) based on these news articles:

{context}

Letter Requirements:
- Reference specific issues and facts from the articles provided
- Make 2-3 specific, actionable requests appropriate for {action_context}
- Use a {tone} tone while maintaining Brian's voice
- Focus on: {focus or 'the general implications for Oklahoma'}
- Keep it concise but impactful (300-400 words)
- Include Brian's signature block at the end
- Address as "Dear {salutation}"

Also provide a brief, compelling subject line (5-10 words).

Format your response as:
SUBJECT: [subject line here]
LETTER:
[letter content here]"""
            else:
                # Default prompt for generic users
                letter_prompt = f"""Based on the following news articles and context, draft a compelling letter to {recipient_title} {recipient_name} ({office_desc}) from a constituent in Oklahoma.

{context}

Requirements for the letter:
1. Start with "Dear {salutation},"
2. Introduce yourself as a constituent from {sender_info.get('city', 'Oklahoma')}
3. Reference the specific news/issues from the articles
4. Clearly state your position and concerns
5. Include specific, actionable requests appropriate for {action_context}
6. Use a {tone} tone
7. Include relevant facts from the articles
8. Keep it concise but impactful (300-400 words)
9. End professionally with a call to action

Also provide a brief, compelling subject line (5-10 words) that captures the essence of the letter.

Format your response as:
SUBJECT: [subject line here]
LETTER:
[letter content here]"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": letter_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            # Parse the response
            full_response = response.choices[0].message.content
            lines = full_response.split('\n')

            subject = ""
            letter_body = []
            in_letter = False

            for line in lines:
                if line.startswith('SUBJECT:'):
                    subject = line.replace('SUBJECT:', '').strip()
                elif line.startswith('LETTER:'):
                    in_letter = True
                elif in_letter:
                    letter_body.append(line)

            # Clean up the letter body
            letter_text = '\n'.join(letter_body).strip()

            # If parsing failed, use the whole response as the letter
            if not subject or not letter_text:
                logger.warning("Could not parse AI response properly, using fallback")
                subject = "Important Matter Requiring Your Attention"
                letter_text = full_response

            return subject, letter_text

        except Exception as e:
            logger.error(f"Error drafting letter: {e}")
            # Return a basic template if AI fails
            return self._fallback_letter(articles, sender_info)

    def _fallback_letter(self, articles: List[Dict[str, str]], sender_info: Dict[str, str]) -> Tuple[str, str]:
        """Fallback letter template if AI fails"""
        subject = "Constituent Concern Regarding Recent News"

        article_titles = [article['title'] for article in articles]
        article_list = '\n'.join([f"- {title}" for title in article_titles])

        letter = f"""Dear Senator Mullin,

I am writing to you as a concerned constituent from {sender_info.get('city', 'Oklahoma')}, Oklahoma, regarding recent news developments that have significant implications for our state and nation.

I have been following these recent news stories:
{article_list}

These issues are of great importance to me and many other Oklahomans. I believe they deserve your immediate attention and action in the Senate.

[Please customize this section with your specific concerns and requests based on the articles]

I urge you to:
1. Review these matters carefully
2. Consider the impact on Oklahoma families and businesses
3. Take appropriate action in the Senate
4. Keep your constituents informed of your position and actions

Thank you for your service to Oklahoma. I look forward to your response and learning about the actions you will take on these important matters.

Sincerely,
{sender_info.get('first_name', '')} {sender_info.get('last_name', '')}"""

        return subject, letter

    def refine_letter(self,
                     original_letter: str,
                     feedback: str) -> str:
        """Refine a letter based on user feedback"""
        try:
            prompt = f"""Please revise the following letter based on this feedback:

ORIGINAL LETTER:
{original_letter}

FEEDBACK:
{feedback}

Please provide the revised letter maintaining the same general structure but incorporating the requested changes."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error refining letter: {e}")
            return original_letter

    def personalize_letter_for_recipient(self,
                                        base_letter: str,
                                        base_subject: str,
                                        recipient: Dict,
                                        articles: List[Dict],
                                        tone: str,
                                        focus: str,
                                        variation_index: int) -> Tuple[str, str]:
        """Generate a personalized variation of the letter for a specific recipient"""
        try:
            # Determine personalization factors
            office_type = recipient.get('office_type', '')
            is_federal = office_type in ['federal_senate', 'federal_house']
            is_state = office_type in ['state_senate', 'state_house', 'governor']
            is_executive = office_type == 'governor'
            district = recipient.get('district', '')

            # Create variation instructions based on recipient
            variation_instructions = []

            # Office-specific focus
            if is_executive:
                variation_instructions.append("Focus on state executive actions and implementation")
            elif is_federal:
                variation_instructions.append("Emphasize federal policy implications and national impact")
            elif is_state:
                variation_instructions.append("Highlight state-level concerns and local community impact")

            # District-specific if applicable
            if district:
                variation_instructions.append(f"Reference District {district} specific concerns when relevant")

            # Vary the approach based on index
            approach_variations = [
                "Lead with personal impact and constituent stories",
                "Emphasize data and statistical evidence",
                "Focus on constitutional and legal precedents",
                "Highlight economic implications",
                "Stress moral and ethical considerations",
                "Connect to historical context and past policies"
            ]
            variation_instructions.append(approach_variations[variation_index % len(approach_variations)])

            # Vary the call to action
            action_variations = [
                "Request a town hall or public meeting",
                "Ask for specific legislative action or vote",
                "Request a written response addressing concerns",
                "Propose specific policy solutions",
                "Ask for committee consideration or hearings",
                "Request collaboration with other officials"
            ]
            variation_instructions.append(action_variations[variation_index % len(action_variations)])

            prompt = f"""You need to create a personalized variation of this letter for {recipient['title']} {recipient['name']}.

Original letter to another official:
{base_letter}

Recipient details:
- Name: {recipient['name']}
- Title: {recipient['title']}
- Office Type: {office_type}
- Organization: {recipient.get('organization', '')}

Personalization requirements:
{chr(10).join(f"- {inst}" for inst in variation_instructions)}

Create a unique version that:
1. Addresses {recipient['title']} {recipient['name'].split()[-1]} specifically
2. Varies the structure and phrasing from the original
3. Maintains the core message about {focus}
4. Uses a {tone} tone
5. References the same news/issues but with different emphasis
6. Has a unique opening and closing
7. Varies sentence structure and word choices
8. Is NOT a form letter - should feel personally written

Return the personalized letter with format:
SUBJECT: [new subject line variation]
LETTER:
[personalized letter content]"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.85,  # Higher temperature for more variation
                max_tokens=1500
            )

            # Parse response
            full_response = response.choices[0].message.content
            lines = full_response.split('\n')

            subject = base_subject  # Default
            letter_body = []
            in_letter = False

            for line in lines:
                if line.startswith('SUBJECT:'):
                    subject = line.replace('SUBJECT:', '').strip()
                elif line.startswith('LETTER:'):
                    in_letter = True
                elif in_letter:
                    letter_body.append(line)

            personalized_letter = '\n'.join(letter_body).strip()

            if not personalized_letter:
                logger.warning(f"Personalization failed for {recipient['name']}, using base letter")
                personalized_letter = base_letter

            return subject, personalized_letter

        except Exception as e:
            logger.error(f"Error personalizing letter for {recipient['name']}: {e}")
            # Return base letter with minor modifications
            personalized_letter = base_letter.replace(
                "Dear Senator", f"Dear {recipient['title'].split()[-1]}"
            ).replace(
                "Senator Mullin", f"{recipient['title'].split()[-1]} {recipient['name'].split()[-1]}"
            )
            return base_subject, personalized_letter


# ==================== MAILER JSON GENERATOR ====================

class MailerJSONGenerator:
    """Generates JSON objects for the mailer PDF system"""

    def __init__(self):
        # Load return address from environment variables
        self.return_address = self._load_return_address()

        # Load recipients from CSV
        self.recipients = self._load_recipients()

        # Current selected recipient
        self.current_recipient = None

    def _load_return_address(self) -> Dict:
        """Load return address from sender.json or environment variables"""
        sender_file = 'sender.json'

        # Try loading from sender.json first
        if os.path.exists(sender_file):
            try:
                with open(sender_file, 'r', encoding='utf-8') as f:
                    sender_data = json.load(f)
                    logger.info(f"Loaded sender information from {sender_file}")
                    # Extract just the address fields we need
                    return {
                        'name': sender_data.get('name', 'Brian West'),
                        'street_1': sender_data.get('street_1', '714 E Osage Ave'),
                        'street_2': sender_data.get('street_2', ''),
                        'city': sender_data.get('city', 'McAlester'),
                        'state': sender_data.get('state', 'OK'),
                        'zip': sender_data.get('zip', '74501-6638'),
                        'phone': sender_data.get('phone', '(918) 424-9378'),
                        'email': sender_data.get('email', 'brian@mcalester.net'),
                        'title': sender_data.get('title', '')
                    }
            except Exception as e:
                logger.warning(f"Could not load sender.json: {e}, falling back to environment variables")

        # Fallback to environment variables
        return {
            'name': os.getenv('RETURN_NAME', 'Brian West'),
            'street_1': os.getenv('RETURN_STREET', '714 E Osage Ave'),
            'street_2': os.getenv('RETURN_STREET2', ''),
            'city': os.getenv('RETURN_CITY', 'McAlester'),
            'state': os.getenv('RETURN_STATE', 'OK'),
            'zip': os.getenv('RETURN_ZIP', '74501-6638'),
            'phone': os.getenv('RETURN_PHONE', '(918) 424-9378'),
            'email': os.getenv('RETURN_EMAIL', 'brian@mcalester.net')
        }

    def _load_recipients(self) -> List[Dict]:
        """Load recipients from JSON file"""
        recipients = []
        json_file = 'recipients.json'
        csv_file = 'recipients_export.csv'  # Fallback

        # Try JSON first
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Process federal officials
                if 'federal' in data:
                    # Federal Senate
                    for senator in data['federal'].get('senate', []):
                        for office_key, office in senator.get('offices', {}).items():
                            recipients.append({
                                'id': f"{senator['id']}_{office_key}",
                                'full_name': senator['full_name'],
                                'name': senator['name'],
                                'title': senator['title'],
                                'honorific': senator['honorific'],
                                'organization': 'United States Senate',
                                'street_1': office['street_1'],
                                'street_2': office.get('street_2', ''),
                                'city': office['city'],
                                'state': office['state'],
                                'zip': office['zip'],
                                'phone': office.get('phone', ''),
                                'office_type': 'federal_senate',
                                'office_location': office_key,
                                'office_name': office['name'],
                                'party': senator.get('party', '')
                            })

                    # Federal House
                    for rep in data['federal'].get('house', []):
                        for office_key, office in rep.get('offices', {}).items():
                            recipients.append({
                                'id': f"{rep['id']}_{office_key}",
                                'full_name': rep['full_name'],
                                'name': rep['name'],
                                'title': rep['title'],
                                'honorific': rep['honorific'],
                                'organization': 'United States House of Representatives',
                                'street_1': office['street_1'],
                                'street_2': office.get('street_2', ''),
                                'city': office['city'],
                                'state': office['state'],
                                'zip': office['zip'],
                                'phone': office.get('phone', ''),
                                'office_type': 'federal_house',
                                'office_location': office_key,
                                'office_name': office['name'],
                                'district': rep.get('district', ''),
                                'party': rep.get('party', '')
                            })

                # Process state officials
                if 'state' in data:
                    # Governor
                    if 'executive' in data['state'] and 'governor' in data['state']['executive']:
                        gov = data['state']['executive']['governor']
                        for office_key, office in gov.get('offices', {}).items():
                            recipients.append({
                                'id': f"{gov['id']}_{office_key}",
                                'full_name': gov['full_name'],
                                'name': gov['name'],
                                'title': gov['title'],
                                'honorific': gov['honorific'],
                                'organization': 'Office of the Governor',
                                'street_1': office['street_1'],
                                'street_2': office.get('street_2', ''),
                                'city': office['city'],
                                'state': office['state'],
                                'zip': office['zip'],
                                'phone': office.get('phone', ''),
                                'office_type': 'governor',
                                'office_location': office_key,
                                'office_name': office['name'],
                                'party': gov.get('party', '')
                            })

                    # State Senate
                    for senator in data['state'].get('senate', []):
                        for office_key, office in senator.get('offices', {}).items():
                            recipients.append({
                                'id': f"{senator['id']}_{office_key}",
                                'full_name': senator['full_name'],
                                'name': senator['name'],
                                'title': senator['title'],
                                'honorific': senator['honorific'],
                                'organization': 'Oklahoma State Senate',
                                'street_1': office['street_1'],
                                'street_2': office.get('street_2', ''),
                                'city': office['city'],
                                'state': office['state'],
                                'zip': office['zip'],
                                'phone': office.get('phone', ''),
                                'office_type': 'state_senate',
                                'office_location': office_key,
                                'office_name': office['name'],
                                'district': senator.get('district', ''),
                                'party': senator.get('party', '')
                            })

                    # State House
                    for rep in data['state'].get('house', []):
                        for office_key, office in rep.get('offices', {}).items():
                            recipients.append({
                                'id': f"{rep['id']}_{office_key}",
                                'full_name': rep['full_name'],
                                'name': rep['name'],
                                'title': rep['title'],
                                'honorific': rep['honorific'],
                                'organization': 'Oklahoma House of Representatives',
                                'street_1': office['street_1'],
                                'street_2': office.get('street_2', ''),
                                'city': office['city'],
                                'state': office['state'],
                                'zip': office['zip'],
                                'phone': office.get('phone', ''),
                                'office_type': 'state_house',
                                'office_location': office_key,
                                'office_name': office['name'],
                                'district': rep.get('district', ''),
                                'party': rep.get('party', '')
                            })

                if recipients:
                    logger.info(f"Loaded {len(recipients)} recipients from {json_file}")
                    return recipients

            except Exception as e:
                logger.warning(f"Error loading JSON file: {e}, trying CSV fallback")

        # Fallback to CSV if JSON not found or failed
        if os.path.exists(csv_file):
            logger.info("Using CSV fallback for recipients")
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        full_name = row.get('name_text', '').strip()

                        # Simple parsing for CSV fallback
                        if 'Governor' in full_name:
                            office_type = 'governor'
                            title = 'Governor of Oklahoma'
                            organization = 'Office of the Governor'
                        elif 'Senator' in full_name and ('Lankford' in full_name or 'Mullin' in full_name):
                            office_type = 'federal_senate'
                            title = 'United States Senator'
                            organization = 'United States Senate'
                        elif 'Congressman' in full_name or 'Congresswoman' in full_name:
                            office_type = 'federal_house'
                            title = 'United States Representative'
                            organization = 'United States House of Representatives'
                        elif 'Senator' in full_name:
                            office_type = 'state_senate'
                            title = 'State Senator'
                            organization = 'Oklahoma State Senate'
                        elif 'Representative' in full_name:
                            office_type = 'state_house'
                            title = 'State Representative'
                            organization = 'Oklahoma House of Representatives'
                        else:
                            office_type = 'unknown'
                            title = ''
                            organization = ''

                        name = full_name.replace('Governor ', '').replace('Senator ', '').replace('Representative ', '').replace('Congressman ', '')

                        recipients.append({
                            'id': idx,
                            'full_name': full_name,
                            'name': name,
                            'title': title,
                            'honorific': 'The Honorable',
                            'organization': organization,
                            'street_1': row.get('address1_text', ''),
                            'street_2': '',
                            'city': row.get('City', 'Oklahoma City'),
                            'state': row.get('state_text', 'OK'),
                            'zip': row.get('zip_text', ''),
                            'office_type': office_type
                        })

            except Exception as e:
                logger.error(f"Error loading CSV file: {e}")

        # Final fallback
        if not recipients:
            logger.warning("No recipients file found, using default")
            return [{
                'id': 'mullin_dc',
                'full_name': 'Senator Markwayne Mullin',
                'name': 'Markwayne Mullin',
                'title': 'United States Senator',
                'honorific': 'The Honorable',
                'organization': 'United States Senate',
                'street_1': '316 Hart Senate Office Building',
                'street_2': '',
                'city': 'Washington',
                'state': 'DC',
                'zip': '20510',
                'office_type': 'federal_senate',
                'office_location': 'dc'
            }]

        return recipients

    def set_recipient(self, recipient: Dict):
        """Set the current recipient"""
        self.current_recipient = recipient

    @property
    def default_positioning(self):
        """Default positioning for standard #10 envelope"""
        return {
            'unit': 'inches',
            'margins': {
                'top': 1.25,
                'bottom': 1.25,
                'left': 1.25,
                'right': 1.25
            },
            'return_address': {
                'x': 0.5,
                'y': 0.625,
                'width': 3.5,
                'height': 1.0
            },
            'recipient_address': {
                'x': 0.75,
                'y': 2.0625,
                'width': 4.0,
                'height': 1.125
            },
            'date_position': {
                'x': 4.875,
                'y': 1.7,
                'alignment': 'right'
            },
            'body_start_y': 3.67
        }

    @property
    def default_formatting(self):
        """Default formatting for letters"""
        return {
            'font_family': 'Times-Roman',
            'font_size': 11,
            'line_spacing': 1.5,
            'paragraph_spacing': 12,
            'justify_body': False,
            'indent_paragraphs': True,
            'indent_size': 0.5
        }

    def parse_letter_content(self, letter_text: str) -> Dict[str, any]:
        """Parse the AI-generated letter into components"""
        lines = letter_text.strip().split('\n')

        # Find salutation (starts with "Dear")
        salutation_idx = 0

        # Determine default salutation based on current recipient
        if self.current_recipient:
            office_type = self.current_recipient.get('office_type', '')
            name = self.current_recipient.get('name', '')

            if office_type == 'governor':
                default_salutation = f"Dear Governor {name.split()[-1]}"
            elif office_type in ['federal_senate', 'state_senate']:
                default_salutation = f"Dear Senator {name.split()[-1]}"
            elif office_type in ['federal_house', 'state_house']:
                default_salutation = f"Dear Representative {name.split()[-1]}"
            else:
                default_salutation = f"Dear {name}"
        else:
            default_salutation = "Dear Senator Mullin"

        salutation = default_salutation
        for i, line in enumerate(lines):
            if line.strip().startswith("Dear"):
                salutation = line.strip().rstrip(',')
                salutation_idx = i
                break

        # Find closing (Sincerely, Respectfully, etc.)
        closing_idx = len(lines) - 1
        closing = "Respectfully"
        closing_keywords = ['Sincerely', 'Respectfully', 'Best regards', 'Thank you', 'Yours truly']

        for i in range(len(lines) - 1, salutation_idx, -1):
            line = lines[i].strip().rstrip(',')
            if any(keyword in line for keyword in closing_keywords):
                closing = line
                closing_idx = i
                break

        # Extract body paragraphs (between salutation and closing)
        body_lines = lines[salutation_idx + 1:closing_idx]

        # Group lines into paragraphs
        paragraphs = []
        current_paragraph = []

        for line in body_lines:
            line = line.strip()
            if line:
                # Check if it's a heading (ALL CAPS, short)
                if line.isupper() and len(line.split()) <= 10:
                    # Add current paragraph if exists
                    if current_paragraph:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                    # Add heading as separate element
                    paragraphs.append(line)
                else:
                    current_paragraph.append(line)
            elif current_paragraph:
                # Empty line means end of paragraph
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []

        # Add last paragraph if exists
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))

        # Remove any signature block lines that might have been included
        cleaned_paragraphs = []
        for para in paragraphs:
            # Skip lines that look like signature block
            if not any(skip in para for skip in ['Brian West', '714 E Osage', 'McAlester', '918', 'brian@']):
                cleaned_paragraphs.append(para)

        return {
            'salutation': salutation,
            'body': cleaned_paragraphs,
            'closing': closing
        }

    def generate_mailer_json(self,
                           subject: str,
                           letter_text: str,
                           category: str = 'General',
                           custom_return_address: Optional[Dict] = None,
                           date: Optional[str] = None) -> Dict:
        """Generate complete JSON object for mailer system"""

        if not self.current_recipient:
            raise ValueError("No recipient selected. Call set_recipient() first.")

        # Parse the letter content
        content_parts = self.parse_letter_content(letter_text)

        # Set date
        letter_date = date or datetime.now().strftime('%Y-%m-%d')

        # Determine document type based on office type
        doc_type = 'congressional'
        if self.current_recipient['office_type'] in ['state_house', 'state_senate']:
            doc_type = 'state_legislative'
        elif self.current_recipient['office_type'] == 'governor':
            doc_type = 'executive'

        # Build the JSON object
        mailer_json = {
            'metadata': {
                'type': doc_type,
                'date': letter_date,
                'date_format': 'full',
                'reference_id': f"{self.current_recipient['name'].replace(' ', '_').upper()}_{category.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            },
            'positioning': self.default_positioning,
            'return_address': custom_return_address or self.return_address,
            'recipient_address': {
                'honorific': self.current_recipient.get('honorific', 'The Honorable'),
                'name': self.current_recipient['name'],
                'title': self.current_recipient.get('title', ''),
                'organization': self.current_recipient.get('organization', ''),
                'street_1': self.current_recipient['street_1'],
                'street_2': self.current_recipient.get('street_2', ''),
                'city': self.current_recipient['city'],
                'state': self.current_recipient['state'],
                'zip': self.current_recipient['zip']
            },
            'content': {
                'salutation': content_parts['salutation'],
                'subject': f"RE: {subject}",
                'body': content_parts['body'],
                'closing': content_parts['closing'],
                'signature': {
                    'type': 'typed',
                    'typed_name': (custom_return_address or self.return_address).get('name', 'Brian West'),
                    'title': (custom_return_address or self.return_address).get('title', '')
                }
            },
            'formatting': self.default_formatting,
            'fold_lines': {
                'enabled': True,
                'positions': [3.67, 7.33],
                'style': {
                    'line_length_mm': 4,
                    'margin_offset_mm': 3,
                    'color': '#CCCCCC',
                    'line_width': 0.5,
                    'line_style': 'solid'
                }
            },
            'header': {
                'page_1': {
                    'enabled': False,
                    'left': '',
                    'center': '',
                    'right': ''
                },
                'subsequent': {
                    'enabled': True,
                    'left': self.current_recipient['name'],
                    'center': 'Page {page}',
                    'right': '{formatted_date}'
                },
                'font_size': 10,
                'color': '#333333',
                'line_below': True
            },
            'footer': {
                'enabled': True,
                'left': '',
                'center': 'Page {page} of {total}',
                'right': '',
                'font_size': 10,
                'color': '#666666',
                'line_above': True
            },
            'page_settings': {
                'paper_size': 'letter',
                'orientation': 'portrait',
                'page_numbers': {
                    'show': True,
                    'position': 'bottom_center',
                    'start_on_page': 1
                }
            }
        }

        # Add postscript if the letter mentions enclosures or cc
        if 'enclos' in letter_text.lower():
            mailer_json['content']['enclosures'] = ['Documents as referenced']

        return mailer_json

    def save_json(self, mailer_json: Dict, output_dir: str = 'mailer_output') -> str:
        """Save the JSON to a file"""
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ref_id = mailer_json['metadata'].get('reference_id', f'letter_{timestamp}')
        filename = f"{output_dir}/{ref_id}.json"

        # Save JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(mailer_json, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved mailer JSON to: {filename}")
        return filename


# ==================== INTERACTIVE SYSTEM ====================

class InteractiveMailerSystem:
    """Interactive system for generating mailer JSON files"""

    def __init__(self):
        self.fetcher = NewsArticleFetcher()
        self.drafter = AILetterDrafter()
        self.json_generator = MailerJSONGenerator()

        # Session data
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_data = {
            'session_id': self.session_id,
            'start_time': datetime.now().isoformat(),
            'news_articles': [],
            'drafts': [],
            'revisions': [],
            'final_letter': None,
            'mailer_json': None,
            'output_files': [],
            'ai_interactions': [],
            'user_edits': []
        }

        # Configuration
        self.config = self._load_config()

        # Topic categories
        self.topic_keywords = {
            'Agriculture': ['farm', 'agriculture', 'crops', 'livestock', 'farmer', 'ranch', 'usda'],
            'Banking': ['bank', 'financial', 'credit', 'loan', 'mortgage', 'fdic', 'federal reserve'],
            'Budget': ['budget', 'spending', 'deficit', 'debt', 'appropriation', 'fiscal'],
            'Defense': ['military', 'defense', 'pentagon', 'army', 'navy', 'air force', 'veteran'],
            'Education': ['school', 'education', 'student', 'teacher', 'university', 'college'],
            'Energy': ['energy', 'oil', 'gas', 'renewable', 'solar', 'wind', 'pipeline', 'electricity'],
            'Environment': ['environment', 'climate', 'pollution', 'conservation', 'epa', 'clean'],
            'Foreign Affairs': ['foreign', 'international', 'treaty', 'embassy', 'diplomatic'],
            'Government Reform': ['government', 'reform', 'regulation', 'bureaucracy', 'accountability'],
            'Health Care': ['health', 'medical', 'medicare', 'medicaid', 'insurance', 'hospital', 'doctor'],
            'Homeland Security': ['security', 'terrorism', 'border', 'immigration', 'customs', 'tsa'],
            'Immigration': ['immigration', 'immigrant', 'visa', 'citizenship', 'refugee', 'asylum'],
            'Judiciary': ['court', 'judge', 'justice', 'legal', 'law', 'constitution'],
            'Labor': ['labor', 'union', 'worker', 'employment', 'wage', 'workplace', 'osha'],
            'Social Security': ['social security', 'retirement', 'pension', 'disability', 'elderly'],
            'Taxes': ['tax', 'irs', 'revenue', 'deduction', 'credit', 'taxation'],
            'Telecommunications': ['telecom', 'internet', 'broadband', 'fcc', 'network', 'cable'],
            'Trade': ['trade', 'tariff', 'export', 'import', 'nafta', 'commerce'],
            'Transportation': ['transportation', 'highway', 'road', 'bridge', 'transit', 'infrastructure'],
            'Veterans': ['veteran', 'va', 'military service', 'gi bill', 'vfw']
        }

        # Detect available editors
        self.editor = self._detect_editor()

    def _load_config(self) -> Dict:
        """Load configuration from sender.json or defaults"""
        sender_file = 'sender.json'

        # Default configuration
        config = {
            'first_name': 'Brian',
            'last_name': 'West',
            'street_address': '714 E Osage Ave',
            'city': 'McAlester',
            'state': 'OK',
            'zip_code': '74501-6638',
            'phone': '(918) 424-9378',
            'email': 'brian@mcalester.net',
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview'),
        }

        # Try loading from sender.json
        if os.path.exists(sender_file):
            try:
                with open(sender_file, 'r', encoding='utf-8') as f:
                    sender_data = json.load(f)
                    # Update config with sender data
                    config.update({
                        'first_name': sender_data.get('first_name', 'Brian'),
                        'last_name': sender_data.get('last_name', 'West'),
                        'street_address': sender_data.get('street_1', '714 E Osage Ave'),
                        'city': sender_data.get('city', 'McAlester'),
                        'state': sender_data.get('state', 'OK'),
                        'zip_code': sender_data.get('zip', '74501-6638'),
                        'phone': sender_data.get('phone', '(918) 424-9378'),
                        'email': sender_data.get('email', 'brian@mcalester.net'),
                    })
            except Exception as e:
                logger.warning(f"Could not load sender config from sender.json: {e}")

        return config

    def _detect_editor(self) -> str:
        """Detect available text editor"""
        editor = os.getenv('VISUAL') or os.getenv('EDITOR')
        if editor:
            return editor

        editors_to_try = ['nano', 'vim', 'vi', 'emacs', 'code', 'subl', 'notepad']
        for ed in editors_to_try:
            if self._command_exists(ed):
                return ed

        return 'vi' if platform.system() != 'Windows' else 'notepad'

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except:
            return False

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if platform.system() == 'Windows' else 'clear')

    def display_header(self, title: str):
        """Display a formatted header"""
        self.clear_screen()
        print("=" * 70)
        print(f" {title.center(68)} ")
        print("=" * 70)

    def collect_news_articles(self) -> List[str]:
        """Interactively collect news article URLs"""
        self.display_header("STEP 1: COLLECT NEWS ARTICLES")

        print("\n📰 Provide news article URLs for the issue you want to address.")
        print("These will be analyzed to draft your letter to Senator Mullin.\n")

        urls = []
        while True:
            print(f"Article #{len(urls) + 1} (press Enter when done)")
            url = input("URL: ").strip()

            if not url:
                if urls:
                    break
                else:
                    print("⚠️  Please provide at least one news article URL.\n")
                    continue

            if not (url.startswith('http://') or url.startswith('https://')):
                print("⚠️  Please enter a valid URL starting with http:// or https://\n")
                continue

            urls.append(url)
            print(f"✓ Added article #{len(urls)}\n")

            if len(urls) >= 5:
                another = input("Add another article? (y/n): ").strip().lower()
                if another != 'y':
                    break

        return urls

    def fetch_and_analyze_articles(self, urls: List[str]) -> List[Dict]:
        """Fetch and display article summaries"""
        self.display_header("STEP 2: ANALYZING ARTICLES")

        articles = []
        for i, url in enumerate(urls, 1):
            print(f"\n📥 Fetching article {i}/{len(urls)}...")
            print(f"   URL: {url}")

            article = self.fetcher.fetch_article(url)
            articles.append(article)

            self.session_data['news_articles'].append({
                'url': article['url'],
                'title': article['title'],
                'source': article['source'],
                'length': len(article['text']),
                'fetched_at': datetime.now().isoformat()
            })

            print(f"   ✓ Title: {article['title'][:60]}...")
            print(f"   ✓ Source: {article['source']}")
            print(f"   ✓ Content: {len(article['text'])} characters")

        input("\n✓ All articles fetched. Press Enter to continue...")
        return articles

    def detect_topic_category(self, articles: List[Dict], letter_content: str = "") -> str:
        """Use AI to detect the most appropriate topic category"""
        print("\n🤖 Analyzing content to determine topic category...")

        combined_text = " ".join([a['text'][:1000] for a in articles])
        if letter_content:
            combined_text += " " + letter_content

        scores = {}
        for category, keywords in self.topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in combined_text.lower())
            if score > 0:
                scores[category] = score

        if scores:
            detected_category = max(scores, key=scores.get)
            confidence = "high" if scores[detected_category] > 3 else "medium"
        else:
            detected_category = "General"
            confidence = "low"

        try:
            prompt = f"""Based on these article titles, what is the most appropriate category?

Articles:
{chr(10).join([f"- {a['title']}" for a in articles])}

Categories: Agriculture, Banking, Budget, Defense, Education, Energy, Environment,
Foreign Affairs, Government Reform, Health Care, Homeland Security,
Immigration, Judiciary, Labor, Social Security, Taxes, Telecommunications,
Trade, Transportation, Veterans, General

Respond with just the category name."""

            response = self.drafter.client.chat.completions.create(
                model=self.drafter.model,
                messages=[
                    {"role": "system", "content": "You are a categorization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )

            ai_category = response.choices[0].message.content.strip()
            valid_categories = list(self.topic_keywords.keys()) + ['General']
            if ai_category in valid_categories:
                detected_category = ai_category
                confidence = "high"

            self.session_data['ai_interactions'].append({
                'type': 'category_detection',
                'result': ai_category,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            logger.warning(f"AI category detection failed: {e}")

        print(f"   ✓ Detected category: {detected_category} (confidence: {confidence})")

        print(f"\n📂 Suggested category: {detected_category}")
        use_suggested = input("Use this category? (y/n): ").strip().lower()

        if use_suggested != 'y':
            print("\nAvailable categories:")
            categories = list(self.topic_keywords.keys()) + ['General']
            for i, cat in enumerate(categories, 1):
                print(f"{i:2}. {cat}")

            while True:
                try:
                    choice = int(input("\nSelect category number: ").strip())
                    if 1 <= choice <= len(categories):
                        detected_category = categories[choice - 1]
                        break
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Please enter a number.")

        return detected_category

    def generate_focus_options(self, articles: List[Dict]) -> List[str]:
        """Use AI to generate contextually relevant focus options based on articles"""
        try:
            # Prepare article summaries
            article_summaries = []
            for article in articles[:3]:  # Use first 3 articles to avoid token limits
                summary = f"Title: {article['title']}\nKey points: {article['text'][:500]}"
                article_summaries.append(summary)

            prompt = f"""Based on these news articles about issues affecting Oklahoma, generate 6 specific focus areas that would be relevant for a constituent letter to a government official.

Articles:
{chr(10).join(article_summaries)}

Generate 6 focus options that are:
1. Specific to the issues in these articles
2. Relevant to Oklahoma constituents
3. Actionable for government officials
4. Clear and concise (10-15 words each)

Format as a numbered list, one focus per line. Examples of good focus areas:
- Impact on rural Oklahoma communities and farmers
- Effects on working families' healthcare costs
- Constitutional implications for civil liberties
- Economic consequences for small businesses
- Environmental impact on local water resources
- Effects on veterans and military families

Return ONLY the 6 numbered focus options, nothing else."""

            response = self.drafter.client.chat.completions.create(
                model=self.drafter.model,
                messages=[
                    {"role": "system", "content": "You are a policy analyst helping constituents identify key focus areas for their letters to officials."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )

            focus_text = response.choices[0].message.content.strip()

            # Parse the numbered list
            focus_options = []
            for line in focus_text.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove number, dash, or bullet and clean up
                    cleaned = line.lstrip('0123456789.-•').strip()
                    if cleaned:
                        focus_options.append(cleaned)

            # Ensure we have at least 6 options (add defaults if needed)
            default_options = [
                "Impact on rural Oklahoma communities",
                "Economic effects on working families",
                "Constitutional and democratic principles",
                "Healthcare access and affordability",
                "Education and workforce development",
                "Infrastructure and public services"
            ]

            while len(focus_options) < 6:
                if default_options:
                    focus_options.append(default_options.pop(0))

            return focus_options[:6]  # Return only first 6

        except Exception as e:
            logger.warning(f"Could not generate AI focus options: {e}")
            # Return default options if AI fails
            return [
                "Impact on rural Oklahoma communities",
                "Economic effects on working families",
                "Constitutional and democratic principles",
                "Healthcare access and affordability",
                "Education and workforce development",
                "Infrastructure and public services"
            ]

    def select_tone_and_focus(self, articles: Optional[List[Dict]] = None) -> Tuple[str, str, str]:
        """Interactive selection of tone and focus"""
        self.display_header("STEP 3: CUSTOMIZE YOUR LETTER")

        print("\n🎯 Select the tone for your letter:\n")
        tones = {
            '1': ('professional', 'Formal and respectful, focusing on facts'),
            '2': ('concerned', 'Expressing worry about the issue'),
            '3': ('urgent', 'Emphasizing immediate action needed'),
            '4': ('supportive', 'Showing support for specific positions')
        }

        for key, (tone, desc) in tones.items():
            print(f"  {key}. {tone.capitalize():<15} - {desc}")

        tone_choice = input("\nSelect tone (1-4): ").strip() or '1'
        tone = tones.get(tone_choice, tones['1'])[0]

        print("\n📍 Select the focus for your letter:")

        # Generate AI-based focus options if articles are provided
        if articles:
            print("Analyzing articles to suggest relevant focus areas...\n")
            focus_options = self.generate_focus_options(articles)
        else:
            focus_options = [
                "Impact on rural Oklahoma communities",
                "Economic effects on working families",
                "Constitutional and democratic principles",
                "Healthcare access and affordability",
                "Education and workforce development",
                "Infrastructure and public services"
            ]

        # Display numbered options
        for i, option in enumerate(focus_options, 1):
            print(f"  {i}. {option}")
        print(f"  7. Custom (write your own)")

        # Get user selection
        while True:
            choice = input("\nSelect focus (1-7): ").strip()

            if choice == '7':
                focus = input("Enter your custom focus: ").strip()
                if not focus:
                    focus = "General policy implications for Oklahoma"
                break
            elif choice in ['1', '2', '3', '4', '5', '6']:
                focus = focus_options[int(choice) - 1]
                break
            elif not choice:
                focus = "General policy implications for Oklahoma"
                break
            else:
                print("Invalid selection. Please choose 1-7.")

        print("\n📝 Any additional context or specific requests?")
        context = input("Additional context (or Enter to skip): ").strip()

        return tone, focus, context

    def select_recipients(self) -> List[Dict]:
        """Select multiple officials and their specific office addresses"""
        self.display_header("SELECT RECIPIENTS")

        print("\n📮 Select officials to send letters to:")
        print("   You can select multiple recipients.\n")

        # Group unique officials by type (combine multiple offices per official)
        officials_data = {}  # official_id -> {info, offices}

        for recipient in self.json_generator.recipients:
            official_id = recipient.get('id', '').split('_')[0]  # Get base ID without office

            if official_id not in officials_data:
                officials_data[official_id] = {
                    'info': recipient,
                    'offices': []
                }

            officials_data[official_id]['offices'].append(recipient)

        # Group by type for display
        federal_senate = []
        federal_house = []
        state_senate = []
        state_house = []
        governor = []

        for official_id, data in officials_data.items():
            info = data['info']
            if info['office_type'] == 'federal_senate':
                federal_senate.append((official_id, data))
            elif info['office_type'] == 'federal_house':
                federal_house.append((official_id, data))
            elif info['office_type'] == 'state_senate':
                state_senate.append((official_id, data))
            elif info['office_type'] == 'state_house':
                state_house.append((official_id, data))
            elif info['office_type'] == 'governor':
                governor.append((official_id, data))

        # Display officials grouped by type
        all_officials = []
        idx = 1

        if governor:
            print("🏛️  GOVERNOR:")
            for official_id, data in governor:
                info = data['info']
                offices_count = len(data['offices'])
                district = f" - District {info.get('district')}" if info.get('district') else ""
                office_text = f" ({offices_count} office{'s' if offices_count > 1 else ''})" if offices_count > 1 else ""
                print(f"  {idx:2}. {info['full_name']}{district}{office_text}")
                all_officials.append((official_id, data))
                idx += 1
            print()

        if federal_senate:
            print("🇺🇸 U.S. SENATORS:")
            for official_id, data in federal_senate:
                info = data['info']
                offices_count = len(data['offices'])
                office_text = f" ({offices_count} offices)" if offices_count > 1 else ""
                print(f"  {idx:2}. {info['full_name']}{office_text}")
                all_officials.append((official_id, data))
                idx += 1
            print()

        if federal_house:
            print("🏛️  U.S. REPRESENTATIVES:")
            for official_id, data in federal_house:
                info = data['info']
                offices_count = len(data['offices'])
                district = f" - District {info.get('district')}" if info.get('district') else ""
                office_text = f" ({offices_count} offices)" if offices_count > 1 else ""
                print(f"  {idx:2}. {info['full_name']}{district}{office_text}")
                all_officials.append((official_id, data))
                idx += 1
            print()

        if state_senate:
            print("🏛️  STATE SENATORS:")
            for official_id, data in state_senate:
                info = data['info']
                offices_count = len(data['offices'])
                district = f" - District {info.get('district')}" if info.get('district') else ""
                office_text = f" ({offices_count} office{'s' if offices_count > 1 else ''})" if offices_count > 1 else ""
                print(f"  {idx:2}. {info['full_name']}{district}{office_text}")
                all_officials.append((official_id, data))
                idx += 1
            print()

        if state_house:
            print("🏛️  STATE REPRESENTATIVES:")
            for official_id, data in state_house:
                info = data['info']
                offices_count = len(data['offices'])
                district = f" - District {info.get('district')}" if info.get('district') else ""
                office_text = f" ({offices_count} office{'s' if offices_count > 1 else ''})" if offices_count > 1 else ""
                print(f"  {idx:2}. {info['full_name']}{district}{office_text}")
                all_officials.append((official_id, data))
                idx += 1

        # Get user selections
        print("\n📋 Enter recipient numbers separated by commas (e.g., 1,3,5)")
        print("   Or enter 'all' to select all recipients")
        print("   Or enter 'federal' for all federal officials")
        print("   Or enter 'state' for all state officials")
        print("   Or enter 'federal-dc' for federal officials (DC offices)")
        print("   Or enter 'federal-local' for federal officials (local offices)")
        print("   Or enter 'state-local' for state officials (local offices)")

        while True:
            selection = input("\nYour selection: ").strip().lower()

            selected_officials = []
            preset_office_choice = None  # Will be 'dc' or 'local' for batch office selection

            if selection == 'all':
                selected_officials = all_officials.copy()
            elif selection == 'federal':
                selected_officials = [(oid, data) for oid, data in all_officials
                                     if data['info']['office_type'] in ['federal_senate', 'federal_house']]
            elif selection == 'state':
                selected_officials = [(oid, data) for oid, data in all_officials
                                     if data['info']['office_type'] in ['state_senate', 'state_house', 'governor']]
            elif selection == 'federal-dc':
                selected_officials = [(oid, data) for oid, data in all_officials
                                     if data['info']['office_type'] in ['federal_senate', 'federal_house']]
                preset_office_choice = 'dc'
                print("✓ Selecting federal officials with DC offices...")
            elif selection == 'federal-local':
                selected_officials = [(oid, data) for oid, data in all_officials
                                     if data['info']['office_type'] in ['federal_senate', 'federal_house']]
                preset_office_choice = 'local'
                print("✓ Selecting federal officials with local offices...")
            elif selection == 'state-local':
                selected_officials = [(oid, data) for oid, data in all_officials
                                     if data['info']['office_type'] in ['state_senate', 'state_house', 'governor']]
                preset_office_choice = 'local'
                print("✓ Selecting state officials with local offices...")
            else:
                # Parse comma-separated numbers
                try:
                    indices = [int(x.strip()) for x in selection.split(',')]
                    for idx in indices:
                        if 1 <= idx <= len(all_officials):
                            selected_officials.append(all_officials[idx - 1])
                        else:
                            print(f"⚠️  Number {idx} is out of range")
                except ValueError:
                    print("⚠️  Please enter valid numbers separated by commas, or 'all', 'federal', or 'state'")
                    continue

            if selected_officials:
                print(f"\n✓ Selected {len(selected_officials)} official(s)")

                # Now select specific offices for each official
                final_recipients = []

                # Check if any officials have multiple offices
                has_multi_office = any(len(data['offices']) > 1 for _, data in selected_officials)

                # Use preset office choice if specified (from federal-dc, federal-local, state-local)
                if preset_office_choice:
                    batch_choice = '1' if preset_office_choice == 'dc' else '2'
                elif has_multi_office:
                    print("\n📍 Office Selection:")
                    print("   Some officials have multiple offices.")
                    print("   Choose how to proceed:")
                    print("   1. Select DC offices for all (where available)")
                    print("   2. Select local/state offices for all (where available)")
                    print("   3. Choose individually for each official")

                    batch_choice = input("\nYour choice (1-3, default 3): ").strip() or '3'
                else:
                    batch_choice = None

                if batch_choice == '1':
                    # Select DC offices where available
                    print("\n✓ Selecting DC offices where available...")
                    for official_id, data in selected_officials:
                        offices = data['offices']
                        dc_office = None
                        for office in offices:
                            if office.get('office_location') == 'dc' or office['state'] == 'DC':
                                dc_office = office
                                break
                        # Use DC office if available, otherwise first office
                        selected = dc_office if dc_office else offices[0]
                        final_recipients.append(selected)
                        print(f"   • {selected['full_name']}: {selected.get('office_name', selected['city'])}")

                elif batch_choice == '2':
                    # Select local offices where available
                    print("\n✓ Selecting local offices where available...")
                    for official_id, data in selected_officials:
                        offices = data['offices']
                        local_office = None
                        for office in offices:
                            if office['state'] == 'OK':
                                local_office = office
                                break
                        # Use local office if available, otherwise first office
                        selected = local_office if local_office else offices[0]
                        final_recipients.append(selected)
                        print(f"   • {selected['full_name']}: {selected.get('office_name', selected['city'])}")

                elif batch_choice == '3' or (batch_choice is None and has_multi_office):
                    # Individual selection
                    print("\n📍 Select office location for each official:")
                    for official_id, data in selected_officials:
                        info = data['info']
                        offices = data['offices']

                        if len(offices) == 1:
                            # Only one office, auto-select
                            final_recipients.append(offices[0])
                            print(f"\n✓ {info['full_name']}: {offices[0].get('office_name', offices[0]['city'])}")
                        else:
                            # Multiple offices, let user choose
                            print(f"\n{info['full_name']} has {len(offices)} offices:")
                            for i, office in enumerate(offices, 1):
                                office_name = office.get('office_name', f"{office['city']} Office")
                                print(f"  {i}. {office_name}")
                                print(f"     {office['street_1']}, {office['city']}, {office['state']}")

                            # Check if this official has DC and local offices
                            has_dc = any(o.get('office_location') == 'dc' or o['state'] == 'DC'
                                        for o in offices)
                            has_local = any(o['state'] == 'OK' for o in offices)

                            if has_dc and has_local:
                                print(f"\n   Or type 'dc' for Washington office")
                                print(f"   Or type 'local' for Oklahoma office")

                            while True:
                                choice = input(f"\nSelect office (1-{len(offices)}): ").strip().lower()

                                selected_office = None

                                # Check for DC/local shortcuts
                                if choice == 'dc' and has_dc:
                                    for office in offices:
                                        if office.get('office_location') == 'dc' or office['state'] == 'DC':
                                            selected_office = office
                                            break
                                elif choice == 'local' and has_local:
                                    for office in offices:
                                        if office['state'] == 'OK':
                                            selected_office = office
                                            break
                                else:
                                    # Try numeric selection
                                    try:
                                        office_idx = int(choice) - 1
                                        if 0 <= office_idx < len(offices):
                                            selected_office = offices[office_idx]
                                    except ValueError:
                                        pass

                                if selected_office:
                                    final_recipients.append(selected_office)
                                    print(f"✓ Selected: {selected_office.get('office_name', selected_office['city'])}")
                                    break
                                else:
                                    print("Invalid selection. Please try again.")
                else:
                    # No multi-office officials, just add all
                    for official_id, data in selected_officials:
                        final_recipients.append(data['offices'][0])

                print(f"\n📊 Final Selection Summary:")
                print(f"   {len(final_recipients)} recipient(s) with specific offices:")
                for r in final_recipients:
                    office_name = r.get('office_name', f"{r['city']} Office")
                    print(f"   • {r['full_name']} - {office_name}")

                confirm = input("\nConfirm selection? (y/n): ").strip().lower()
                if confirm == 'y':
                    return final_recipients
            else:
                print("⚠️  No recipients selected. Please try again.")

    def select_office(self) -> str:
        """Select which Senator office to address the letter to"""
        print("\n📮 Select Senator Mullin's office:")
        print("1. Washington DC (Main office)")
        print("2. Tulsa, OK")
        print("3. Oklahoma City, OK")

        choice = input("\nSelect office (1-3, default 1): ").strip() or '1'

        office_map = {
            '1': 'dc',
            '2': 'tulsa',
            '3': 'oklahoma_city'
        }

        return office_map.get(choice, 'dc')

    def draft_letter_with_ai(self, articles: List[Dict], tone: str, focus: str, context: str, recipient: Dict) -> Tuple[str, str]:
        """Draft letter using AI"""
        self.display_header("STEP 4: AI LETTER DRAFTING")

        print(f"\n🤖 AI is analyzing articles and drafting your letter to {recipient['name']}...")
        print("   Using Brian West's progressive voice...\n")

        sender_info = {
            'first_name': self.config['first_name'],
            'last_name': self.config['last_name'],
            'city': self.config['city'],
            'state': self.config['state']
        }

        subject, letter = self.drafter.draft_letter(
            articles=articles,
            sender_info=sender_info,
            tone=tone,
            focus=focus,
            additional_context=context,
            recipient=recipient
        )

        self.session_data['drafts'].append({
            'version': len(self.session_data['drafts']) + 1,
            'subject': subject,
            'letter': letter,
            'tone': tone,
            'focus': focus,
            'context': context,
            'timestamp': datetime.now().isoformat()
        })

        print("✓ Letter drafted successfully!")
        input("\nPress Enter to review...")

        return subject, letter

    def open_in_editor(self, content: str) -> str:
        """Open content in visual editor"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_file = f.name

        try:
            print(f"\n📝 Opening in {self.editor}...")
            print("   (Save and exit when done)")
            time.sleep(1)

            subprocess.call([self.editor, temp_file])

            with open(temp_file, 'r') as f:
                edited_content = f.read()

            return edited_content

        finally:
            try:
                os.unlink(temp_file)
            except:
                pass

    def review_and_edit_loop(self, subject: str, letter: str, articles: List[Dict],
                            tone: str, focus: str, context: str, recipient: Dict,
                            base_letter: str = None) -> Tuple[str, str]:
        """Interactive review and edit loop"""

        while True:
            self.display_header("LETTER REVIEW AND EDITING")

            # Show recipient info if available
            if recipient:
                print(f"\n📮 RECIPIENT: {recipient.get('full_name', 'Unknown')}")
                office_name = recipient.get('office_name', f"{recipient.get('city', 'Unknown')} Office")
                print(f"📍 OFFICE: {office_name}")

            print(f"\n📧 SUBJECT: {subject}\n")
            print("-" * 70)
            print(letter)
            print("-" * 70)

            print("\n🔧 OPTIONS:")
            print("  1. Accept and generate mailer JSON")
            print("  2. Edit in visual editor")
            print("  3. Request AI revision")
            print("  4. Regenerate with different tone/focus")
            print("  5. View source articles")
            if base_letter and base_letter != letter:
                print("  6. Compare with base letter")
                print("  7. Save draft and exit")
                print("  8. Discard and exit")
            else:
                print("  6. Save draft and exit")
                print("  7. Discard and exit")

            max_choice = '8' if (base_letter and base_letter != letter) else '7'
            choice = input(f"\nYour choice (1-{max_choice}): ").strip()

            if choice == '1':
                self.session_data['final_letter'] = {
                    'subject': subject,
                    'letter': letter,
                    'accepted_at': datetime.now().isoformat()
                }
                return subject, letter

            elif choice == '2':
                print("\n📝 Opening letter in editor...")
                edit_content = f"SUBJECT: {subject}\n\n{letter}"
                edited = self.open_in_editor(edit_content)

                lines = edited.split('\n')
                if lines[0].startswith('SUBJECT:'):
                    subject = lines[0].replace('SUBJECT:', '').strip()
                    letter = '\n'.join(lines[2:]).strip()
                else:
                    letter = edited.strip()

                self.session_data['user_edits'].append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'visual_editor'
                })

                print("\n✓ Letter updated")
                input("Press Enter to continue...")

            elif choice == '3':
                print("\n💬 What would you like to change?")
                feedback = input("Your feedback: ").strip()

                if feedback:
                    print("\n🤖 Revising letter...")
                    revised_letter = self.drafter.refine_letter(letter, feedback)

                    self.session_data['revisions'].append({
                        'feedback': feedback,
                        'original': letter,
                        'revised': revised_letter,
                        'timestamp': datetime.now().isoformat()
                    })

                    letter = revised_letter
                    print("✓ Letter revised!")
                    input("Press Enter to continue...")

            elif choice == '4':
                print("\n🔄 Let's regenerate...")
                new_tone, new_focus, new_context = self.select_tone_and_focus(articles)

                print("\n🤖 Regenerating letter...")
                new_subject, new_letter = self.drafter.draft_letter(
                    articles=articles,
                    sender_info={
                        'first_name': self.config['first_name'],
                        'last_name': self.config['last_name'],
                        'city': self.config['city'],
                        'state': self.config['state']
                    },
                    tone=new_tone,
                    focus=new_focus,
                    additional_context=new_context,
                    recipient=recipient
                )

                self.session_data['drafts'].append({
                    'version': len(self.session_data['drafts']) + 1,
                    'subject': new_subject,
                    'letter': new_letter,
                    'tone': new_tone,
                    'focus': new_focus,
                    'context': new_context,
                    'timestamp': datetime.now().isoformat()
                })

                subject = new_subject
                letter = new_letter
                print("✓ Letter regenerated!")
                input("Press Enter to continue...")

            elif choice == '5':
                print("\n📰 SOURCE ARTICLES:")
                print("-" * 70)
                for i, article in enumerate(articles, 1):
                    print(f"\n{i}. {article['title']}")
                    print(f"   Source: {article['source']}")
                    print(f"   URL: {article['url']}")

                input("\nPress Enter to return...")

            elif choice == '6' and base_letter and base_letter != letter:
                # Compare with base letter
                print("\n📊 LETTER COMPARISON:")
                print("-" * 70)
                print("\n🔵 BASE LETTER (template):")
                print("-" * 35)
                print(base_letter[:500] + "..." if len(base_letter) > 500 else base_letter)
                print("\n🔶 PERSONALIZED LETTER (current):")
                print("-" * 35)
                print(letter[:500] + "..." if len(letter) > 500 else letter)
                print("-" * 70)
                input("\nPress Enter to return...")

            elif choice == '6' and not (base_letter and base_letter != letter):
                self.save_session()
                print("\n✓ Draft saved")
                return None, None

            elif choice == '7' and not (base_letter and base_letter != letter):
                confirm = input("\n⚠️  Discard all changes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    return None, None

            elif choice == '7' and base_letter and base_letter != letter:
                self.save_session()
                print("\n✓ Draft saved")
                return None, None

            elif choice == '8' and base_letter and base_letter != letter:
                confirm = input("\n⚠️  Discard all changes? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    return None, None

            else:
                print("\n⚠️  Invalid choice")
                input("Press Enter to continue...")

    def generate_mailer_json(self, subject: str, letter: str, category: str) -> Dict:
        """Generate JSON for mailer system"""
        self.display_header("GENERATING MAILER JSON")

        print("\n📄 Generating JSON for mailer PDF system...")

        # Generate the JSON
        mailer_json = self.json_generator.generate_mailer_json(
            subject=subject,
            letter_text=letter,
            category=category
        )

        # Store in session
        self.session_data['mailer_json'] = mailer_json

        print("✓ JSON generated successfully!")
        return mailer_json

    def save_outputs(self, mailer_json: Dict, subject: str, letter: str):
        """Save all output files"""
        output_dir = f"mailer_output/{self.session_id}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename based on recipient
        recipient = self.json_generator.current_recipient
        if recipient:
            recipient_name = recipient.get('name', 'official').lower().replace(' ', '_')
            json_filename = f"letter_to_{recipient_name}.json"
        else:
            json_filename = "letter_to_official.json"

        # Save mailer JSON
        json_file = f"{output_dir}/{json_filename}"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(mailer_json, f, indent=2, ensure_ascii=False)
        self.session_data['output_files'].append(json_file)

        # Save plain text letter
        text_file = f"{output_dir}/letter_plain.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"SUBJECT: {subject}\n\n{letter}")
        self.session_data['output_files'].append(text_file)

        # Save session data
        session_file = f"{output_dir}/session.data"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        self.session_data['output_files'].append(session_file)

        print(f"\n📁 Files saved to: {output_dir}/")
        print(f"   • {json_filename} - Ready for mailer PDF generation")
        print(f"   • letter_plain.txt - Plain text version")
        print(f"   • session.data - Complete session history")

        return output_dir

    def save_session(self):
        """Save session data"""
        session_file = f"session_{self.session_id}.data"
        self.session_data['end_time'] = datetime.now().isoformat()

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)

        print(f"📁 Session saved to: {session_file}")

    def run(self):
        """Main execution flow"""
        try:
            # Welcome screen
            self.display_header("AI LETTER GENERATOR")

            print(f"\n👤 Brian West - Progressive Constitutional Democrat")
            print(f"📍 McAlester, Oklahoma")
            print(f"🤖 AI Model: {self.config['openai_model']}")
            print(f"📝 Editor: {self.editor}")
            print(f"📜 Using Brian West's progressive voice")

            input("\nPress Enter to begin...")

            # Step 1: Select recipients (multiple)
            recipients = self.select_recipients()
            self.session_data['recipients'] = recipients

            # Step 2: Collect news articles
            urls = self.collect_news_articles()

            # Step 3: Fetch and analyze
            articles = self.fetch_and_analyze_articles(urls)

            # Step 4: Select tone and focus (with AI-generated options based on articles)
            tone, focus, context = self.select_tone_and_focus(articles)

            # Step 5: Draft base letter for first recipient
            first_recipient = recipients[0]
            self.json_generator.set_recipient(first_recipient)
            subject, letter = self.draft_letter_with_ai(articles, tone, focus, context, first_recipient)

            # Step 6: Detect category
            category = self.detect_topic_category(articles, letter)
            self.session_data['category'] = category

            # Step 7: Review and edit base letter
            print(f"\n📝 Drafting base letter for {first_recipient['name']}...")
            print("   This will be used as the template for personalizing other letters.")

            final_subject, final_letter = self.review_and_edit_loop(
                subject, letter, articles, tone, focus, context, first_recipient
            )

            if final_subject and final_letter:
                # Step 8: Generate personalized letters for all recipients
                self.display_header("GENERATING PERSONALIZED LETTERS")

                print(f"\n📧 Generating {len(recipients)} personalized letters...")
                print("   Each letter will be uniquely tailored to the recipient.")

                # Ask if user wants to review each letter
                review_each = 'n'
                if len(recipients) > 1:
                    print("\n🔍 Review Options:")
                    print("   Would you like to review and edit each personalized letter?")
                    print("   (If no, all letters will be generated automatically)")
                    review_each = input("\n   Review each letter? (y/n, default n): ").strip().lower() or 'n'

                generated_letters = []
                output_dir = f"mailer_output/{self.session_id}"
                Path(output_dir).mkdir(parents=True, exist_ok=True)

                for i, recipient in enumerate(recipients, 1):
                    print(f"\n{i}/{len(recipients)} - {recipient['full_name']}...")

                    # Set current recipient
                    self.json_generator.set_recipient(recipient)

                    # Generate personalized version if not the first recipient
                    if i == 1:
                        # Use the reviewed letter for first recipient
                        personalized_subject = final_subject
                        personalized_letter = final_letter
                    else:
                        # Create unique variation for other recipients
                        print(f"   🤖 Generating personalized version...")
                        personalized_subject, personalized_letter = self.drafter.personalize_letter_for_recipient(
                            base_letter=final_letter,
                            base_subject=final_subject,
                            recipient=recipient,
                            articles=articles,
                            tone=tone,
                            focus=focus,
                            variation_index=i
                        )

                        # Allow review and editing if requested
                        if review_each == 'y':
                            print(f"\n📝 Review letter for {recipient['full_name']}")
                            print(f"   Office: {recipient.get('office_name', recipient['city'])}")

                            # If there are more recipients, offer option to skip remaining reviews
                            if i < len(recipients):
                                print(f"   ({len(recipients) - i} more letters remaining)")
                                print("\n   Options:")
                                print("   1. Review this letter")
                                print("   2. Accept this letter and all remaining without review")
                                print("   3. Accept this letter and continue reviewing others")

                                review_choice = input("\n   Your choice (1-3, default 1): ").strip() or '1'

                                if review_choice == '2':
                                    # Accept all remaining without review
                                    review_each = 'n'
                                    print("   ✓ Accepting this and all remaining letters without review")
                                elif review_choice == '3':
                                    # Just accept this one
                                    print("   ✓ Accepting this letter without review")
                                else:
                                    # Review this letter
                                    personalized_subject, personalized_letter = self.review_and_edit_loop(
                                        personalized_subject, personalized_letter, articles, tone, focus, context, recipient,
                                        base_letter=final_letter
                                    )
                            else:
                                # Last recipient, just review
                                personalized_subject, personalized_letter = self.review_and_edit_loop(
                                    personalized_subject, personalized_letter, articles, tone, focus, context, recipient,
                                    base_letter=final_letter
                                )

                    # Generate JSON for this recipient
                    mailer_json = self.json_generator.generate_mailer_json(
                        subject=personalized_subject,
                        letter_text=personalized_letter,
                        category=category
                    )

                    # Save letter files
                    recipient_name_lower = recipient.get('name', 'official').lower().replace(' ', '_')
                    json_filename = f"letter_to_{recipient_name_lower}.json"
                    json_file = f"{output_dir}/{json_filename}"

                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(mailer_json, f, indent=2, ensure_ascii=False)

                    # Save plain text version too
                    text_file = f"{output_dir}/letter_to_{recipient_name_lower}.txt"
                    with open(text_file, 'w', encoding='utf-8') as f:
                        f.write(f"TO: {recipient['full_name']}\n")
                        f.write(f"TITLE: {recipient['title']}\n")
                        f.write(f"SUBJECT: {personalized_subject}\n\n")
                        f.write(personalized_letter)

                    generated_letters.append({
                        'recipient': recipient,
                        'subject': personalized_subject,
                        'json_file': json_filename,
                        'text_file': f"letter_to_{recipient_name_lower}.txt"
                    })

                    print(f"   ✓ Generated: {json_filename}")

                # Save session data with all letters
                self.session_data['generated_letters'] = generated_letters
                self.session_data['output_files'] = [f"{output_dir}/{g['json_file']}" for g in generated_letters]

                session_file = f"{output_dir}/session.data"
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(self.session_data, f, indent=2, ensure_ascii=False)

                # Final screen
                self.display_header("ALL LETTERS GENERATED!")

                print(f"\n✅ SUCCESS! Generated {len(generated_letters)} personalized letters!")
                print(f"\n📊 Session Summary:")
                print(f"  • Recipients: {len(recipients)}")
                print(f"  • Articles analyzed: {len(articles)}")
                print(f"  • Category: {category}")
                print(f"  • Output directory: {output_dir}")

                print(f"\n📄 Generated Letters:")
                for gl in generated_letters:
                    print(f"  • {gl['recipient']['full_name']}")
                    print(f"    - {gl['json_file']}")

                print(f"\n🚀 Next Steps:")
                print(f"  1. Navigate to the mailer project:")
                print(f"     cd ../mailer")
                print(f"  2. Generate PDFs for all letters:")
                print(f"     for json in ../markwayne/{output_dir}/*.json; do")
                print(f"       python mailer.py \"$json\"")
                print(f"     done")
                print(f"  3. Review the generated PDFs")
                print(f"  4. Print and mail to recipients")

            else:
                print("\n❌ Letter generation cancelled")

            # Save session
            self.save_session()

        except KeyboardInterrupt:
            print("\n\n⚠️  Session interrupted")
            self.save_session()
            sys.exit(0)

        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\n❌ An error occurred: {e}")
            self.save_session()
            sys.exit(1)


# ==================== MAIN ENTRY POINT ====================

def main():
    """Main entry point"""
    # Check prerequisites
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ ERROR: OpenAI API key not found!")
        print("\nPlease add your OpenAI API key to the .env file:")
        print("  OPENAI_API_KEY=sk-...")
        print("\nGet your API key from: https://platform.openai.com/api-keys")
        sys.exit(1)

    # Run the interactive system
    system = InteractiveMailerSystem()
    system.run()


if __name__ == "__main__":
    main()