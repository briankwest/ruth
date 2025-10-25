#!/bin/bash

# Complete Workflow: From News to PDF-Ready Letter
# This script demonstrates the entire process

echo "================================================"
echo " Complete Letter Generation Workflow"
echo "================================================"
echo ""

# Check prerequisites
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Please copy .env.example to .env and add your OpenAI API key"
    exit 1
fi

if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  OpenAI API key not configured in .env"
    exit 1
fi

# Step 1: Run interactive mailer to generate JSON
echo "STEP 1: Generating Letter with AI"
echo "---------------------------------"
echo "This will:"
echo "  • Collect news URLs"
echo "  • Draft letter with AI"
echo "  • Allow editing and revisions"
echo "  • Generate JSON for mailer"
echo ""
read -p "Ready to start? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 ai_writer.py

    # Find the most recent output directory
    LATEST_DIR=$(ls -dt mailer_output/*/ 2>/dev/null | head -1)

    if [ -n "$LATEST_DIR" ]; then
        echo ""
        echo "✅ JSON files generated in: $LATEST_DIR"
        echo ""
        echo "Files created:"
        ls -la "$LATEST_DIR"

        echo ""
        echo "STEP 2: Generate PDF (Optional)"
        echo "-------------------------------"
        echo "To generate a PDF from the JSON:"
        echo ""
        echo "  cd ../mailer"
        # Find the JSON file in the output directory
        JSON_FILE=$(ls ${LATEST_DIR}letter_to_*.json 2>/dev/null | head -1)
        if [ -n "$JSON_FILE" ]; then
            echo "  python mailer.py ../markwayne/$JSON_FILE"
        else
            echo "  python mailer.py ../markwayne/${LATEST_DIR}letter_to_*.json"
        fi
        echo ""
        echo "The PDF will be ready for printing and mailing!"

        # Show the JSON structure
        echo ""
        echo "JSON Preview:"
        echo "-------------"
        head -30 "${LATEST_DIR}letter_to_mullin.json"
        echo "..."
    else
        echo "No output directory found. The process may have been cancelled."
    fi
else
    echo "Workflow cancelled."
fi

echo ""
echo "================================================"
echo " Workflow Complete"
echo "================================================"