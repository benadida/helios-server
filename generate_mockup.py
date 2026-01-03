#!/usr/bin/env python3
"""Generate mockup images of the datetime picker"""

from PIL import Image, ImageDraw, ImageFont
import datetime

def create_datetime_picker_mockup():
    """Create a visual mockup of the new datetime picker"""
    # Create image
    width, height = 900, 700
    img = Image.new('RGB', (width, height), color='#f5f5f5')
    draw = ImageDraw.Draw(img)

    try:
        # Try to use a better font
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
        heading_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
        label_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
    except:
        # Fallback to default font
        title_font = heading_font = label_font = small_font = ImageFont.load_default()

    # Draw white background for content
    draw.rectangle([(30, 30), (870, 670)], fill='white', outline='#ddd', width=2)

    # Title
    draw.text((50, 50), 'Helios Election - New DateTime Picker', fill='#333', font=title_font)
    draw.rectangle([(50, 85), (850, 87)], fill='#4CAF50')

    # Form section background
    draw.rectangle([(50, 110), (850, 280)], fill='#fafafa', outline='#e0e0e0', width=1)

    # Voting Starts At field
    y_pos = 130
    draw.text((70, y_pos), 'Voting Starts At:', fill='#555', font=heading_font)

    # Draw the datetime-local input field
    input_y = y_pos + 30
    draw.rectangle([(70, input_y), (320, input_y + 40)], fill='white', outline='#4CAF50', width=2)
    draw.rectangle([(70, input_y), (320, input_y + 40)], fill='white', outline='#4CAF50', width=1)

    # Add focus glow effect
    for i in range(5):
        alpha = 60 - (i * 10)
        # This creates a glow effect around the input
        draw.rectangle([(70-i, input_y-i), (320+i, input_y + 40+i)],
                      outline=f'#{hex(76)[2:].zfill(2)}{hex(175)[2:].zfill(2)}{hex(80)[2:].zfill(2)}{hex(alpha)[2:].zfill(2)}',
                      width=1)

    # Input value
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M')
    draw.text((80, input_y + 12), date_str, fill='#333', font=label_font)

    # Calendar icon
    draw.rectangle([(280, input_y + 8), (310, input_y + 32)], fill='#e0e0e0', outline='#999', width=1)
    draw.text((287, input_y + 9), '📅', fill='#555', font=label_font)

    # Help text
    draw.text((70, input_y + 50), 'UTC date and time when voting begins', fill='#777', font=small_font)

    # Voting Ends At field
    y_pos = 220
    draw.text((70, y_pos), 'Voting Ends At:', fill='#555', font=heading_font)

    input_y = y_pos + 30
    draw.rectangle([(70, input_y), (320, input_y + 40)], fill='white', outline='#ccc', width=2)

    tomorrow = now + datetime.timedelta(days=1)
    date_str = tomorrow.strftime('%Y-%m-%d %H:%M')
    draw.text((80, input_y + 12), date_str, fill='#333', font=label_font)

    # Calendar icon
    draw.rectangle([(280, input_y + 8), (310, input_y + 32)], fill='#e0e0e0', outline='#999', width=1)
    draw.text((287, input_y + 9), '📅', fill='#555', font=label_font)

    # Help text
    draw.text((70, input_y + 50), 'UTC date and time when voting ends', fill='#777', font=small_font)

    # Features section
    features_y = 320
    draw.text((50, features_y), 'Key Features:', fill='#333', font=heading_font)

    features = [
        '✓ Modern HTML5 datetime-local input',
        '✓ Native browser picker with calendar popup',
        '✓ Green focus highlight for better UX',
        '✓ Replaces 6 dropdown menus with 1 clean input',
        '✓ Mobile-friendly with native controls',
        '✓ Better accessibility and validation'
    ]

    y = features_y + 30
    for feature in features:
        draw.text((70, y), feature, fill='#555', font=label_font)
        y += 25

    # Note at bottom
    note_y = 560
    draw.rectangle([(50, note_y), (850, note_y + 80)], fill='#e3f2fd', outline='#2196F3', width=3)
    draw.text((70, note_y + 15), 'Improvement Summary:', fill='#1976d2', font=heading_font)
    draw.text((70, note_y + 40),
              'Replaced old multi-dropdown datetime picker with modern HTML5 input.',
              fill='#333', font=label_font)
    draw.text((70, note_y + 58),
              'Result: Cleaner UI, better UX, mobile-friendly, and easier to use!',
              fill='#333', font=label_font)

    return img

def create_comparison_mockup():
    """Create a comparison image of old vs new"""
    width, height = 900, 600
    img = Image.new('RGB', (width, height), color='#f5f5f5')
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
        heading_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
        label_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        small_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    except:
        title_font = heading_font = label_font = small_font = ImageFont.load_default()

    # White background
    draw.rectangle([(30, 30), (870, 570)], fill='white', outline='#ddd', width=2)

    # Title
    draw.text((50, 50), 'DateTime Picker: Old vs New Comparison', fill='#333', font=title_font)
    draw.rectangle([(50, 85), (850, 87)], fill='#4CAF50')

    # Left side - OLD
    old_x = 50
    old_y = 120
    draw.rectangle([(old_x, old_y), (old_x + 380, old_y + 380)], fill='#fff9e6', outline='#ffa726', width=2)
    draw.text((old_x + 20, old_y + 15), '❌ OLD: Multiple Dropdowns', fill='#e65100', font=heading_font)

    # Simulate old dropdowns
    dropdown_y = old_y + 60
    draw.text((old_x + 20, dropdown_y), 'Date:', fill='#555', font=label_font)

    # Year dropdown
    draw.rectangle([(old_x + 20, dropdown_y + 25), (old_x + 90, dropdown_y + 50)], fill='white', outline='#999', width=1)
    draw.text((old_x + 30, dropdown_y + 30), '2026 ▼', fill='#333', font=small_font)

    # Month dropdown
    draw.rectangle([(old_x + 100, dropdown_y + 25), (old_x + 200, dropdown_y + 50)], fill='white', outline='#999', width=1)
    draw.text((old_x + 110, dropdown_y + 30), 'January ▼', fill='#333', font=small_font)

    # Day dropdown
    draw.rectangle([(old_x + 210, dropdown_y + 25), (old_x + 270, dropdown_y + 50)], fill='white', outline='#999', width=1)
    draw.text((old_x + 220, dropdown_y + 30), '03 ▼', fill='#333', font=small_font)

    # Time label and dropdowns
    time_y = dropdown_y + 80
    draw.text((old_x + 20, time_y), 'Time:', fill='#555', font=label_font)

    # Hour dropdown
    draw.rectangle([(old_x + 20, time_y + 25), (old_x + 80, time_y + 50)], fill='white', outline='#999', width=1)
    draw.text((old_x + 30, time_y + 30), '14 ▼', fill='#333', font=small_font)

    draw.text((old_x + 88, time_y + 30), ':', fill='#333', font=label_font)

    # Minute dropdown
    draw.rectangle([(old_x + 100, time_y + 25), (old_x + 160, time_y + 50)], fill='white', outline='#999', width=1)
    draw.text((old_x + 110, time_y + 30), '30 ▼', fill='#333', font=small_font)

    # Problems list
    problems_y = time_y + 80
    draw.text((old_x + 20, problems_y), 'Problems:', fill='#d32f2f', font=heading_font)
    problems = [
        '• 6 separate dropdown menus',
        '• Clunky user experience',
        '• Hard to use on mobile',
        '• Takes up lots of space',
        '• Difficult to navigate',
        '• Not modern/intuitive'
    ]
    y = problems_y + 30
    for problem in problems:
        draw.text((old_x + 30, y), problem, fill='#666', font=small_font)
        y += 20

    # Right side - NEW
    new_x = 470
    new_y = 120
    draw.rectangle([(new_x, new_y), (new_x + 380, new_y + 380)], fill='#e8f5e9', outline='#66bb6a', width=2)
    draw.text((new_x + 20, new_y + 15), '✅ NEW: HTML5 DateTime Input', fill='#2e7d32', font=heading_font)

    # Draw new datetime input
    input_y = new_y + 60
    draw.text((new_x + 20, input_y), 'Voting Starts At:', fill='#555', font=label_font)

    draw.rectangle([(new_x + 20, input_y + 25), (new_x + 280, input_y + 65)], fill='white', outline='#4CAF50', width=2)
    draw.text((new_x + 30, input_y + 35), '2026-01-03  14:30', fill='#333', font=label_font)

    # Calendar icon
    draw.rectangle([(new_x + 240, input_y + 33), (new_x + 270, input_y + 57)], fill='#e0e0e0', outline='#999', width=1)
    draw.text((new_x + 247, input_y + 34), '📅', fill='#555', font=label_font)

    # Benefits list
    benefits_y = input_y + 100
    draw.text((new_x + 20, benefits_y), 'Benefits:', fill='#2e7d32', font=heading_font)
    benefits = [
        '• Single, clean input field',
        '• Modern, intuitive interface',
        '• Native calendar popup',
        '• Mobile-friendly controls',
        '• Better accessibility',
        '• Automatic validation',
        '• Green focus highlight',
        '• Saves screen space'
    ]
    y = benefits_y + 30
    for benefit in benefits:
        draw.text((new_x + 30, y), benefit, fill='#666', font=small_font)
        y += 20

    # Bottom note
    draw.rectangle([(50, 520), (850, 560)], fill='#fff3e0', outline='#ff9800', width=2)
    draw.text((70, 532), '💡 Result: Much cleaner, easier to use, and provides a better user experience!',
              fill='#e65100', font=heading_font)

    return img

if __name__ == '__main__':
    print('Generating datetime picker mockup images...')

    # Generate main mockup
    img1 = create_datetime_picker_mockup()
    img1.save('/home/user/helios-server/datetime_picker_mockup.png')
    print('✓ Saved: datetime_picker_mockup.png')

    # Generate comparison mockup
    img2 = create_comparison_mockup()
    img2.save('/home/user/helios-server/datetime_picker_comparison.png')
    print('✓ Saved: datetime_picker_comparison.png')

    print('\nMockup images generated successfully!')
