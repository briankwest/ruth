#!/bin/bash

# Setup script for configuring visual editor
echo "=================================="
echo "Visual Editor Setup for Letter System"
echo "=================================="
echo ""

# Detect current editor settings
current_visual=$VISUAL
current_editor=$EDITOR

if [ -n "$current_visual" ]; then
    echo "Current VISUAL editor: $current_visual"
elif [ -n "$current_editor" ]; then
    echo "Current EDITOR: $current_editor"
else
    echo "No default editor currently set"
fi

echo ""
echo "Available editors on your system:"

# Check for common editors
editors=("nano" "vim" "vi" "emacs" "code" "subl" "atom")
available=()

for editor in "${editors[@]}"; do
    if command -v $editor &> /dev/null; then
        echo "  ✓ $editor"
        available+=($editor)
    fi
done

echo ""
echo "To set your preferred editor, add one of these lines to your .bashrc or .zshrc:"
echo ""
echo "  export VISUAL=nano    # For nano (easiest)"
echo "  export VISUAL=vim     # For vim"
echo "  export VISUAL=code    # For VS Code"
echo ""
echo "Or set it temporarily for this session:"
echo "  export VISUAL=nano"
echo ""

# Ask if they want to set it now
read -p "Would you like to set an editor for this session? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Select an editor:"
    select editor_choice in "${available[@]}" "Cancel"; do
        case $editor_choice in
            "Cancel")
                echo "Setup cancelled"
                break
                ;;
            *)
                if [ -n "$editor_choice" ]; then
                    export VISUAL=$editor_choice
                    echo "✓ VISUAL set to $editor_choice for this session"
                    echo ""
                    echo "To make this permanent, add to your shell config:"
                    echo "  echo 'export VISUAL=$editor_choice' >> ~/.bashrc"
                    echo "  source ~/.bashrc"
                    break
                else
                    echo "Invalid selection"
                fi
                ;;
        esac
    done
fi

echo ""
echo "Setup complete!"