# 🎯 Customizing Your AI Letter Writer's Voice

This guide explains how to configure the AI to write letters that reflect your personal political views, values, and communication style.

## 📋 Overview

The AI Letter Writer uses a custom prompt file (`prompt.md`) to determine:
- Your political perspective and values
- Policy priorities and positions
- Communication tone and style
- How to frame arguments and appeals

Without a custom prompt, the system uses a neutral, professional tone suitable for any constituent.

## 🚀 Quick Start

1. **Copy the example template:**
   ```bash
   cp prompt.md.example prompt.md
   ```

2. **Edit prompt.md with your information:**
   - Replace the example name and address with yours (or leave blank - it uses sender.json)
   - Add your political philosophy and values
   - Define your policy positions
   - Set your preferred tone and style

3. **Test the system:**
   ```bash
   python ai_writer.py
   ```

## 📝 Prompt Structure

Your `prompt.md` file should include these sections:

### 1. Identity Statement
Define who you are as a constituent:
```markdown
You are **[Your Name]**, a constituent from **[Your City, State]**.
You write to elected officials with a **[describe your political perspective]** voice.
```

### 2. Core Values & Beliefs
List your fundamental political principles:
```markdown
## Core Identity & Beliefs

### Constitutional Values
[Your views on democracy, the Constitution, rule of law, etc.]

### Economic Philosophy
[Your stance on free markets, regulation, taxation, etc.]

### Social Values
[Your position on individual rights, community, tradition, etc.]
```

### 3. Policy Positions
Define your stance on specific issues:
```markdown
### Healthcare
- [Your position on healthcare access, insurance, costs]
- [Specific policies you support or oppose]

### Education
- [Your views on public education, school choice, funding]

### Environment
- [Your stance on climate change, conservation, energy]

### Immigration
- [Your position on border security, legal immigration, refugees]
```

### 4. Communication Style
Set the tone for your letters:
```markdown
## Tone & Letter Style

Write letters that are:
- **[Professional/Passionate/Direct/Diplomatic]**
- **[Fact-focused/Story-driven/Data-oriented]**
- **[Formal/Conversational/Urgent/Measured]**

When disagreeing with officials:
- [How to express disagreement respectfully]
- [Whether to reference voting, primaries, etc.]
```

## 🎨 Example Configurations

### Progressive Example
```markdown
You are a **progressive constituent** who believes in:
- Expanding healthcare access through universal coverage
- Bold action on climate change
- Criminal justice reform and racial equity
- Strong social safety nets
- Progressive taxation

Write with **passion and urgency**, using **personal stories** and **moral arguments**.
```

### Conservative Example
```markdown
You are a **conservative constituent** who believes in:
- Limited government and individual liberty
- Free market solutions
- Traditional values and strong families
- Strong national defense
- Fiscal responsibility

Write with **respect for tradition**, using **constitutional arguments** and **economic data**.
```

### Libertarian Example
```markdown
You are a **libertarian constituent** who believes in:
- Maximum individual freedom
- Minimal government intervention
- Free markets without subsidies
- Non-interventionist foreign policy
- Personal responsibility

Write with **logical arguments**, emphasizing **individual rights** and **government overreach**.
```

### Moderate/Centrist Example
```markdown
You are a **moderate constituent** who believes in:
- Pragmatic, bipartisan solutions
- Evidence-based policy making
- Fiscal responsibility with compassion
- Incremental reform over revolution
- Finding common ground

Write with **balanced perspective**, acknowledging **multiple viewpoints** and seeking **compromise**.
```

## 🔧 Advanced Customization

### Issue-Specific Framing
You can specify how to approach specific topics:

```markdown
### When writing about healthcare:
- Emphasize [cost/access/quality/choice]
- Reference [personal experience/statistics/constitutional rights]
- Appeal to [compassion/efficiency/freedom/fairness]

### When writing about taxes:
- Focus on [fairness/growth/services/burden]
- Use [class-based/economic/moral] arguments
```

### Audience-Specific Tone
Adjust tone based on the recipient:

```markdown
### For Republican officials:
- Emphasize [conservative values you share]
- Frame arguments in [their ideological terms]

### For Democratic officials:
- Emphasize [progressive values you share]
- Frame arguments in [their priorities]
```

### Regional/Local Context
Include local perspectives:

```markdown
### Oklahoma-specific context:
- Reference [local industries: oil, gas, agriculture]
- Mention [state-specific challenges]
- Appeal to [Oklahoma values and traditions]
```

## 💡 Tips for Effective Prompts

### DO:
- ✅ Be specific about your values and positions
- ✅ Include nuance where your views don't fit neat categories
- ✅ Specify how to handle controversial topics
- ✅ Define your red lines and non-negotiables
- ✅ Include positive examples of policies you support

### DON'T:
- ❌ Include personal attacks or inflammatory language
- ❌ Advocate for illegal activities
- ❌ Include hate speech or discrimination
- ❌ Make threats or ultimatums
- ❌ Include false or misleading information

## 🔄 Testing Your Prompt

After creating your prompt.md, test it:

1. **Generate a test letter:**
   ```bash
   python ai_writer.py
   ```

2. **Review the output for:**
   - Does it reflect your values?
   - Is the tone appropriate?
   - Are your policy positions clear?

3. **Refine as needed:**
   - Adjust sections that don't sound right
   - Add more specific guidance for issues you care about
   - Fine-tune the tone and style

## 📊 Default Behavior

If you don't create a custom prompt.md, the system uses a neutral default that:
- Maintains professional, respectful tone
- Focuses on facts and evidence
- Avoids partisan language
- Makes clear, specific requests
- Works for any political perspective

This default is suitable for basic constituent communication but won't reflect your personal political views.

## 🔒 Privacy Note

Your `prompt.md` file is:
- **Ignored by git** (won't be committed to version control)
- **Local only** (never sent anywhere except to OpenAI for letter generation)
- **Personal** (reflects your individual views)
- **Replaceable** (can be updated or changed anytime)

## 🆘 Troubleshooting

### Letters don't reflect my values
- Make your prompt.md more specific
- Include explicit policy positions
- Add more examples of desired framing

### Tone is too aggressive/passive
- Adjust the "Tone & Letter Style" section
- Add specific guidelines for disagreement
- Include examples of preferred language

### AI ignores my prompt
- Check that prompt.md exists in the correct location
- Ensure the file isn't empty
- Verify no syntax errors in markdown

### Want different styles for different issues
- Add issue-specific sections
- Include conditional guidance
- Specify different tones for different topics

## 📚 Examples Library

For more prompt examples and templates, consider:
- Creating multiple prompt files (prompt-progressive.md, prompt-conservative.md)
- Switching between them by copying to prompt.md
- Building a library of issue-specific sections
- Sharing templates with like-minded users (outside the git repo)

## 🤝 Contributing

While your personal prompt.md is private, you can:
- Share prompt templates with others
- Contribute examples to documentation
- Suggest improvements to the prompt system
- Help others craft effective prompts

Remember: Your prompt.md is your political voice. Make it authentic to your beliefs and values.