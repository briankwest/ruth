# 📮 AI Letter Writer for Officials

A single-file AI system for generating professional letters to government officials (senators, representatives, governor, state legislators). Analyzes news articles, drafts letters in your personalized voice, and outputs JSON files for the mailer PDF system.

## 🎯 Quick Start

```bash
# 1. Generate personalized letters with AI
python ai_writer.py
# Select multiple recipients (type numbers like 1,3,5 or 'federal' or 'all')
# AI generates unique, personalized letters for each recipient

# 2. Generate PDFs in mailer project
cd ../mailer
# Only processes letter_to_*.json files (session.data is automatically excluded)
for json in ../markwayne/mailer_output/*/*.json; do
  python mailer.py "$json"
done

# 3. Print and mail!
```

## 📜 System Configuration

**⚠️ IMPORTANT: Configure sender.json with YOUR information before using!**

The default configuration uses placeholder "John Doe" information. You MUST update `sender.json` with your real information before sending any letters.

### Customizing Your Voice

The AI can draft letters emphasizing your personal political perspectives. Example themes:
- Constitutional values and democratic principles
- Policy priorities important to you
- Local and national issues you care about
- Your preferred communication style

To customize the AI's writing voice, edit `prompt.md` to match your political views and communication style (see [PROMPT_SYSTEM.md](PROMPT_SYSTEM.md))

## ✨ How It Works

The **ai_writer.py** provides a complete workflow:

1. **🏛️ Select Recipients** - Choose multiple officials (all, federal, state, or specific)
2. **📰 Collect News URLs** - Add articles about issues you care about
3. **🔍 Analyze Articles** - AI extracts key information and context
4. **🎨 Customize Approach** - Choose tone and AI-suggested focus areas
5. **🤖 AI Drafts Base Letter** - Creates initial letter for review
6. **✏️ Visual Editing** - Edit base letter in your preferred editor
7. **🔄 AI Personalization** - Generates unique variations for each recipient:
   - Different opening and closing for each official
   - Varied sentence structure and word choices
   - Office-specific emphasis (federal vs state, executive vs legislative)
   - District-specific references when applicable
   - Different calls to action for each letter
8. **🔍 Review Each Letter** (Optional) - Review and edit personalized versions:
   - Choose to review each personalized letter individually
   - Compare with base template to see changes
   - Edit any personalized letter before saving
   - Skip remaining reviews at any point
9. **📂 Smart Categorization** - Auto-detects appropriate topic
10. **📄 Batch Generation** - Creates JSON and text files for all recipients
11. **💾 Complete Session** - Saves all letters and metadata

### Output Files

```
mailer_output/
└── 20251024_143022/                    # Session timestamp
    ├── letter_to_[recipient_name].json # For PDF generation
    ├── letter_plain.txt                 # Plain text version
    └── session.data                     # Complete session history (not processed by mailer)
```

Examples:
- `letter_to_kevin_stitt.json` (Governor)
- `letter_to_markwayne_mullin.json` (US Senator)
- `letter_to_josh_brecheen.json` (US Representative)

## 🏛️ Supported Officials

The system can generate letters for:
- **Governor** - State executive actions and policies
- **US Senators** - Federal legislation and oversight
- **US Representatives** - Federal legislation and district representation
- **State Senators** - State legislation and district concerns
- **State Representatives** - State legislation and local representation

### 📮 Multi-Recipient Letters (NEW!)

**Generate personalized letters to multiple officials at once:**

- **Select Multiple Recipients**:
  - Type numbers separated by commas: `1,3,5`
  - Select all federal officials: `federal`
  - Select all state officials: `state`
  - Select everyone: `all`
  - **Quick Office Selection (NEW)**:
    - `federal-dc` - Federal officials with DC offices
    - `federal-local` - Federal officials with local offices
    - `state-local` - State officials with local offices

- **Personalized Variations**: Each letter is uniquely tailored:
  - AI generates different variations to avoid form letters
  - Each official gets personalized opening/closing
  - Office-specific policy emphasis
  - Varied sentence structure and vocabulary
  - Different calls to action

- **Individual Review Option (NEW)**:
  - Review and edit each personalized letter
  - Compare personalized letters with base template
  - Accept individual letters or all remaining at once
  - Full editing capabilities for each recipient's letter

- **Efficient Workflow**:
  - Review and edit base letter once
  - AI automatically personalizes for other recipients
  - Batch generate all PDFs with single command

Recipients are loaded from `recipients.json`. The system automatically detects office types based on titles in names (Governor, Senator, Representative, Congressman/woman).

## 🛠️ Setup

### Prerequisites
- Python 3.7+
- OpenAI API key
- Access to the mailer PDF project

### Installation

1. **Clone and navigate to project**
```bash
cd /Users/brian/workdir/markwayne
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

4. **Configure sender information** (REQUIRED)
```bash
cp sender.json.example sender.json
# Edit sender.json with YOUR actual information:
# - Your name and return address
# - Your contact information (phone, email)
# ⚠️  Do not use the example "John Doe" data!
```

5. **Configure AI voice** (optional but recommended)
```bash
cp prompt.md.example prompt.md
# Edit prompt.md to customize the AI's writing style
# Add your political perspectives and communication preferences
```

6. **Verify recipients file**
```bash
# The system uses recipients.json for officials
# Includes all federal and state officials for Oklahoma
# Edit recipients.json to add or modify officials
```

7. **Set up editor (optional)**
```bash
./setup_editor.sh
```

## 📁 Project Structure

```
markwayne/
├── ai_writer.py              # Complete AI letter system (single file)
├── prompt.md                 # Your custom voice configuration (create from .example)
│
├── sender.json              # Your return address and contact info (create from .example)
├── sender.json.example      # Template for sender information
├── prompt.md.example        # Template for custom AI voice
├── recipients.json          # Officials database (federal/state)
│
├── complete_workflow.sh     # Demo workflow script
├── setup_editor.sh         # Editor configuration
│
├── .env                    # Your API key (create from .env.example)
├── .env.example           # Configuration template
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
│
├── README.md             # This file
├── MAILER_WORKFLOW.md   # Workflow documentation
├── PROMPT_SYSTEM.md     # Custom prompt documentation
├── PROJECT_SUMMARY.md   # Cleanup summary
└── mailer_output/            # Generated JSON files (created on first run)
    └── [session_id]/
        ├── letter_to_[recipient].json
        ├── letter_plain.txt
        └── session.data
```

## 📝 Usage Examples

### Basic Interactive Session
```bash
python ai_writer.py
# Follow the prompts to:
# - Select recipient from list
# - Enter news URLs
# - Choose tone (professional/concerned/urgent/supportive)
# - Set focus area
# - Edit letter
# - Select office
```

### Complete Workflow Demo
```bash
./complete_workflow.sh
# Walks through the entire process step by step
```

## 🏢 Senator Offices

The system can address letters to three offices:

- **Washington DC** - Main office (default)
- **Tulsa, OK** - Regional office
- **Oklahoma City, OK** - Regional office

## 🤖 AI Features

- **News Analysis**: Extracts key points from multiple articles
- **Smart Categorization**: Auto-detects topic (Healthcare, Energy, etc.)
- **Voice Consistency**: Maintains your configured perspective from prompt.md
- **Interactive Editing**: Visual editor integration
- **AI Revisions**: Request specific changes ("make it more urgent", etc.)

## 📄 JSON Generation

The system generates JSON compatible with the mailer PDF system:

```json
{
  "metadata": {
    "type": "congressional",
    "date": "2025-10-24",
    "reference_id": "SEN_MULLIN_HEALTHCARE_20251024_143022"
  },
  "return_address": {
    "name": "John Doe",
    "street_1": "123 Main Street",
    "city": "Oklahoma City",
    "state": "OK",
    "zip": "73101-0001"
  },
  "recipient_address": {
    "honorific": "The Honorable",
    "name": "Markwayne Mullin",
    "title": "United States Senator",
    ...
  },
  "content": {
    "salutation": "Dear Senator Mullin",
    "subject": "RE: Your Subject",
    "body": ["paragraph1", "paragraph2", ...],
    "closing": "Respectfully"
  }
}
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4-turbo-preview

# Editor (optional, auto-detected if not set)
VISUAL=nano
```

### Custom Voice (prompt.md)
Edit `prompt.md` to customize the AI's writing style and political perspective.
See [PROMPT_SYSTEM.md](PROMPT_SYSTEM.md) for details.

## 📚 Documentation

- **[MAILER_WORKFLOW.md](MAILER_WORKFLOW.md)** - Detailed workflow guide
- **[PROMPT_SYSTEM.md](PROMPT_SYSTEM.md)** - How to customize AI voice

## 🧪 Testing

```bash
# Run the system with test news URLs
python ai_writer.py
# Use sample news URLs when prompted

# Check generated output
ls -la mailer_output/

# Generate PDF from output
cd ../mailer
python mailer.py ../markwayne/mailer_output/*/letter_to_mullin.json
```

## 📞 Support

For issues or questions:
1. Check the documentation files
2. Review the session logs in `mailer_output/*/session.data`
3. Test with `test_mailer_json.py` to verify setup

## 📜 License

Open source project. Configure `sender.json` and `prompt.md` for your personal use.