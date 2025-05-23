import os
import json
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Base URL of the Notion wiki
BASE_URL = "https://imc-prosperity.notion.site/Prosperity-3-Wiki-19ee8453a09380529731c4e6fb697ea4"
# Directory to save the JSON files
SAVE_DIR = "../../../data/prosperity_wiki"
# Directory to save code files
CODE_DIR = "../../../data/prosperity_wiki/code"

# Make absolute paths for directories
current_dir = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.abspath(os.path.join(current_dir, SAVE_DIR))
CODE_DIR = os.path.abspath(os.path.join(current_dir, CODE_DIR))

def load_code_file_mapping(mapping_file="codefile_names.md"):
    """Load the code file mapping from markdown file"""
    mapping = {}
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(current_dir, mapping_file)
        
        if not os.path.exists(full_path):
            print(f"Warning: Code file mapping not found at {full_path}")
            return mapping
            
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Skip header rows (first two lines)
        for line in lines[2:]:
            if '|' not in line:
                continue
                
            parts = line.strip().split('|')
            if len(parts) >= 4:  # With proper formatting, we should have ['', 'code_X', 'Description', '']
                code_id = parts[1].strip()
                description = parts[2].strip()
                # Use the description as the filename, with a .py extension
                # Replace non-alphanumeric characters (except spaces and hyphens) with underscores
                safe_filename = re.sub(r'[^\w\s\-]', '_', description) + '.py'
                # Store with code_id as the key (like "code_1")
                mapping[code_id] = safe_filename
                print(f"Loaded mapping: {code_id} -> {safe_filename}")
        
        print(f"Loaded {len(mapping)} code file mappings")
    except Exception as e:
        print(f"Error loading code file mapping: {e}")
    
    return mapping

# Load the code file mapping
CODE_FILE_MAPPING = load_code_file_mapping()

def save_json(data, folder, filename):
    """Save data to a JSON file."""
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def determine_category(title, content_blocks):
    """Determine which category the page belongs to based on title and content."""
    title_lower = title.lower()
    
    # Check for round-related pages
    if re.search(r'round \d|tutorial round', title_lower):
        return "rounds"
    
    # Check for e-learning related content
    e_learning_keywords = ["glossary", "resources", "algorithm", "programming", "python", "learning"]
    if any(keyword in title_lower for keyword in e_learning_keywords):
        return "e-learning_center"
    
    # Default to about_prosperity for general information
    return "about_prosperity"

def save_code_file(code_content, language, page_title, code_id):
    """Save code to a separate file and return the file path."""
    filename = None
    
    # If the page is "Writing an Algorithm in Python" 
    if "algorithm" in page_title.lower() and "python" in page_title.lower():
        # Simply look up the code_id directly in our mapping
        if code_id in CODE_FILE_MAPPING:
            filename = CODE_FILE_MAPPING[code_id]
            print(f"Mapped code block {code_id} to: {filename}")
        # Additional check for strange cases where the code_id might be different format
        else:
            # Extract the code block number from the code_id (format: code_X)
            code_number_match = re.search(r'code_(\d+)', code_id)
            if code_number_match:
                simple_code_id = f"code_{code_number_match.group(1)}"
                if simple_code_id in CODE_FILE_MAPPING:
                    filename = CODE_FILE_MAPPING[simple_code_id]
                    print(f"Mapped code block {code_id} to: {filename}")
    
    # Debug output
    if filename:
        print(f"Using mapped filename: {filename}")
    
    # If no match is found, use the default naming scheme
    if not filename:
        # Create sanitized file name base
        sanitized_title = page_title.lower().replace(" ", "_").replace("/", "_")
        
        # Determine file extension based on language
        extension = ".py" if language.lower() == "python" else ".txt"
        
        # Create filename
        filename = f"{sanitized_title}_{code_id}{extension}"
        print(f"Using default naming for {code_id}: {filename}")
    
    # Ensure code directory exists
    os.makedirs(CODE_DIR, exist_ok=True)
    
    # Process code content to fix indentation issues
    processed_code = process_code_content(code_content, language)
    
    # Save the code file with the correct filename
    file_path = os.path.join(CODE_DIR, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(processed_code)
        print(f"Successfully saved code file to: {file_path}")
    except Exception as e:
        print(f"Error saving code file: {e}")
    
    # Return the relative path from the project root
    return os.path.join("code", filename)

def process_code_content(code_content, language):
    """Process code content to fix indentation and formatting issues"""
    if not code_content:
        return ""
    
    # Remove invisible zero-width space characters (U+200B)
    code_content = code_content.replace('\u200b', '')
    
    # Remove language indicator and "Copy" text that sometimes appear at the start
    code_content = re.sub(r'^(Python|JavaScript|HTML|CSS|JSON|TypeScript|Java|C\+\+|C#|Go|Rust|SQL|Bash|Shell)?\s*Copy\s*', '', code_content)
    
    if language.lower() == "python":
        # Python specific processing
        
        # Split into lines
        lines = code_content.split('\n')
        processed_lines = []
        
        # Track current indentation level
        current_indent = 0
        indent_size = 4  # Standard Python indentation
        
        # Keywords that typically increase indentation level for the next line
        indent_keywords = ["if", "else:", "elif", "for", "while", "def", "class", "with", "try:", "except:", "finally:"]
        # Keywords that typically decrease indentation level
        dedent_keywords = ["else:", "elif", "except:", "finally:"]
        
        for i, line in enumerate(lines):
            # Remove excess whitespace but track if the line had content
            stripped_line = line.strip()
            if not stripped_line:
                # Keep empty lines
                processed_lines.append("")
                continue
                
            # Check if the line is broken into separate tokens
            if re.search(r'(\w+)\s+(\w+)', stripped_line) and ":" in stripped_line:
                # This is a line with control flow that might need indentation fixing
                # Try to clean up the excessive spacing
                cleaned_line = re.sub(r'\s+', ' ', stripped_line)
                # Special handling for indentation keywords
                
                # Adjust indentation for this line
                if any(keyword in stripped_line for keyword in dedent_keywords):
                    # This is a continuation line like "else:", reduce indentation
                    current_indent = max(0, current_indent - indent_size)
                    
                indented_line = ' ' * current_indent + cleaned_line
                processed_lines.append(indented_line)
                
                # Adjust indentation for next line if needed
                if any(keyword in stripped_line for keyword in indent_keywords) and stripped_line.endswith(':'):
                    current_indent += indent_size
            else:
                # Regular code line
                indented_line = ' ' * current_indent + stripped_line
                processed_lines.append(indented_line)
                
                # Check for end of blocks (like return, pass, etc.) to decrease indentation
                if stripped_line.startswith("return ") or stripped_line == "return" or stripped_line == "pass" or stripped_line == "break" or stripped_line == "continue":
                    # These might signal the end of a block
                    if i+1 < len(lines) and lines[i+1].strip() and not lines[i+1].strip().startswith(("else:", "elif", "except:", "finally:")):
                        current_indent = max(0, current_indent - indent_size)
        
        return '\n'.join(processed_lines)
    else:
        # For other languages, just clean up excess whitespace
        # We could add more language-specific formatting here
        lines = code_content.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                # Simplify excess whitespace between tokens
                cleaned_line = re.sub(r'\s+', ' ', stripped_line)
                processed_lines.append(cleaned_line)
            else:
                processed_lines.append("")
                
        return '\n'.join(processed_lines)

def extract_content(soup, page_title):
    """Extract content blocks from the Notion page in their natural order."""
    blocks = []
    code_block_counter = 1  # Counter for code blocks
    seen_content = set()  # Track seen content to avoid duplicates
    
    # First get the page title (h1) which is special
    title_div = soup.select_one(".notion-page-block h1")
    if title_div:
        title_text = title_div.get_text().strip()
        if title_text and title_text not in seen_content:
            blocks.append({
                "type": "h1",
                "content": title_text
            })
            seen_content.add(title_text)
    
    # Try multiple strategies to find the main content container
    content_containers = [
        # Strategy 1: Standard Notion class
        soup.select_one(".notion-page-content"),
        # Strategy 2: Try to find content inside a transclusion block
        soup.select_one(".notion-transclusion_reference-block"),
        # Strategy 3: Look for main body content
        soup.select_one("main")
    ]
    
    content_container = None
    for container in content_containers:
        if container:
            content_container = container
            break
            
    # If we still don't have a container, try a broader approach
    if not content_container:
        # Look for any div that might contain our content blocks
        content_container = soup.find('div', {'class': lambda x: x and ('notion-' in x)})
        
    if not content_container:
        # As a last resort, try to get the body
        content_container = soup.body
    
    if not content_container:
        return blocks  # Early return if no content found
    
    # Track consecutive list elements to combine them later
    current_list_type = None
    current_list_items = []
    
    # First, try to find all the header blocks (h2) in the document
    header_blocks = content_container.find_all(
        lambda tag: tag.name == 'h2' or 
                    (tag.get('class') and any('header-block' in c for c in tag.get('class'))) or
                    (tag.find('div', style=lambda s: s and 'font-weight: 600' in s))
    )
    
    # Then find all text blocks
    text_blocks = content_container.find_all(
        lambda tag: (tag.get('class') and any('text-block' in c for c in tag.get('class'))) or
                    (tag.find('div', spellcheck="true"))
    )
    
    # Process the blocks found
    processed_blocks = []
    
    # First process headers
    for header in header_blocks:
        header_text = header.get_text().strip()
        if header_text and header_text not in seen_content:
            processed_blocks.append({
                "tag": header,
                "type": "h2",
                "content": header_text,
                "position": get_element_position(header)
            })
            seen_content.add(header_text)
    
    # Then process text blocks
    for text_block in text_blocks:
        text = text_block.get_text().strip()
        if text and text not in seen_content:
            # Check if this appears to be a header by style or context
            if (text_block.get('style') and 'font-weight: 600' in text_block.get('style')) or \
               (len(text) < 30 and text.strip().endswith(':')):
                processed_blocks.append({
                    "tag": text_block,
                    "type": "h3", 
                    "content": text,
                    "position": get_element_position(text_block)
                })
            else:
                processed_blocks.append({
                    "tag": text_block, 
                    "type": "p",
                    "content": text,
                    "position": get_element_position(text_block)
                })
            seen_content.add(text)
    
    # Sort blocks by their position in the document
    processed_blocks.sort(key=lambda x: x["position"])
    
    # Convert to our final format
    for block in processed_blocks:
        blocks.append({
            "type": block["type"],
            "content": block["content"]
        })
    
    # If we found no blocks but we have a content container, try direct extraction
    if not blocks and content_container:
        # Try to extract all text content directly
        direct_extraction = extract_text_content_from_container(content_container)
        if direct_extraction:
            for block in direct_extraction:
                content = block.get('content', '')
                if content and content not in seen_content:
                    blocks.append(block)
                    seen_content.add(content)
    
    return blocks

def get_element_position(element):
    """
    Calculate the approximate position of an element in the document.
    This helps us maintain the natural reading order.
    """
    # Try to find the element's position using its parents
    parents = list(element.parents)
    
    # Count how far down the element is in the document
    position = 0
    for i, parent in enumerate(parents):
        # Count previous siblings to get a sense of position
        position += len(list(parent.previous_siblings)) * (100 / (i + 1))
        
    # Add direct position from siblings
    position += len(list(element.previous_siblings)) * 100
    
    return position

def extract_text_content_from_container(container):
    """Extract text content directly from a container, as a fallback method."""
    blocks = []
    
    # Try to find heading elements first
    headings = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    for heading in headings:
        heading_text = heading.get_text().strip()
        if heading_text:
            heading_type = heading.name  # Use the actual heading type (h1, h2, etc.)
            blocks.append({
                "type": heading_type,
                "content": heading_text
            })
    
    # Find div blocks that look like paragraphs (have text content)
    # We're looking for blocks that contain text but aren't just container elements
    potential_paragraphs = container.find_all('div', recursive=True)
    
    for div in potential_paragraphs:
        # Skip if this div contains other content-bearing elements
        if div.find(['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']):
            continue
            
        # Skip if this is a utility element or container
        class_attr = div.get('class', [])
        if class_attr and any(c in ' '.join(class_attr) for c in ['container', 'wrapper', 'layout']):
            continue
            
        # Get the text content
        text = div.get_text().strip()
        
        # Skip empty or very short divs (likely spacers)
        if not text or len(text) < 5:
            continue
            
        # Check if this looks like a heading
        if (len(text) < 50 and (
                div.get('style') and ('font-weight:' in div.get('style') or 'font-size:' in div.get('style')) or
                text.strip().endswith(':'))):
            blocks.append({
                "type": "h3",  # Assume it's a subheading
                "content": text
            })
        else:
            blocks.append({
                "type": "p", 
                "content": text
            })
    
    # Process all links
    links = container.find_all('a')
    for link in links:
        href = link.get('href')
        if href and not href.startswith('#'):  # Skip internal page links
            text = link.get_text().strip()
            if text and len(text) > 1:
                blocks.append({
                    "type": "link",
                    "content": text,
                    "href": href
                })
    
    # Deduplicate blocks with the same content
    seen_content = set()
    unique_blocks = []
    
    for block in blocks:
        content = block.get('content', '')
        if content and content not in seen_content:
            seen_content.add(content)
            unique_blocks.append(block)
    
    return unique_blocks

def extract_list_items(list_element, list_style):
    """Extract items from a list element with proper nesting level."""
    items = []
    
    # Different selectors for list items based on Notion's structure
    list_item_selectors = [
        ".notion-list-item", 
        "li",  # Standard list items
        "[data-block-id]"  # Block-based items
    ]
    
    # Try different selectors to find list items
    list_items_elements = []
    for selector in list_item_selectors:
        found_items = list_element.select(selector)
        if found_items:
            list_items_elements = found_items
            break
    
    # If we couldn't find list items with specific selectors, try direct children
    if not list_items_elements:
        list_items_elements = list_element.find_all(recursive=False)
    
    for item in list_items_elements:
        # Extract text content
        text = item.get_text().strip()
        if not text:
            continue
            
        # Determine nesting level based on indentation or class
        level = 0
        
        # Check for indentation in style
        style = item.get('style', '')
        if 'padding-left' in style or 'margin-left' in style:
            # Extract pixels and estimate level
            pixels = re.search(r'(?:padding|margin)-left:\s*(\d+)px', style)
            if pixels:
                # Typically, each indent level is around 24-30px
                level = int(pixels.group(1)) // 24
                
        # Alternatively check for specific classes that indicate nesting
        if "notion-item-indent" in " ".join(item.get('class', [])):
            for cls in item.get('class', []):
                indent_match = re.search(r'notion-item-indent-(\d+)', cls)
                if indent_match:
                    level = int(indent_match.group(1))
        
        items.append({
            "content": text,
            "level": level
        })
    
    return items

def scrape_notion_wiki():
    """Main function to scrape the Notion wiki and save content as JSON."""
    with sync_playwright() as p:
        # Use a more complete browser configuration
        browser = p.chromium.launch(
            headless=False,  # Use headed mode for debugging
            args=['--disable-web-security', '--disable-features=IsolateOrigins', '--disable-site-isolation-trials']
        )
        
        # Create a more complete browser context
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ) 
        
        page = context.new_page()
        print(f"Accessing: {BASE_URL}")
        
        try:
            # Change the wait_until strategy to 'domcontentloaded' instead of 'load'
            page.goto(BASE_URL, timeout=60000, wait_until='domcontentloaded')
            print("Page loaded successfully")
            
        except Exception as e:
            print(f"Error loading page: {e}")
            # Save the error information for debugging
            with open("debug/error_log.txt", "w") as f:
                f.write(f"Error loading page: {e}")
            # Try to take screenshot of whatever did load
            try:
                page.screenshot(path="debug/error_state.png")
            except:
                pass
        
        # Wait for content to load and interact with the page
        try:
            # Wait longer for the page to load completely
            print("Waiting for page content to load...")
            page.wait_for_timeout(15000)
            
            # Try to find and interact with page elements
            print("Scrolling page to trigger content loading...")
            # Scroll down to trigger lazy loading
            page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight / 2);
                setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 2000);
            """)
            page.wait_for_timeout(5000)
            
            # Try to click any "Show more" or expand buttons
            try:
                expand_buttons = page.query_selector_all('button:has-text("Show more")')
                for button in expand_buttons:
                    button.click()
                    page.wait_for_timeout(1000)
            except Exception as e:
                print(f"No expand buttons found: {e}")
                
        except Exception as e:
            print(f"Error during page interaction: {e}")
        
        # Try multiple selector strategies to find links
        internal_links = set()
        
        # Strategy 1: Standard link selector
        try:
            print("Looking for links with standard selector...")
            links = page.query_selector_all('a[href*="notion.site"]')
            for link in links:
                href = link.get_attribute('href')
                if href and "notion.site" in href and "Prosperity-3" in href:
                    internal_links.add(href.split('?')[0])  # Remove URL parameters
        except Exception as e:
            print(f"Error with standard link selector: {e}")
            
        # Strategy 2: Notion specific selectors
        try:
            print("Looking for links with Notion-specific selectors...")
            notion_links = page.query_selector_all('.notion-link-token a, .notion-selectable a, .notion-page-block a')
            for link in notion_links:
                href = link.get_attribute('href')
                if href and "notion.site" in href:
                    internal_links.add(href.split('?')[0])
        except Exception as e:
            print(f"Error with Notion-specific selector: {e}")
            
        # Strategy 3: JavaScript execution to extract links
        try:
            print("Extracting links using JavaScript...")
            links_from_js = page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a'));
                    return links
                        .filter(a => a.href && a.href.includes('notion.site'))
                        .map(a => a.href.split('?')[0]);
                }
            """)
            for link in links_from_js:
                if "Prosperity-3" in link or "prosperity" in link.lower():
                    internal_links.add(link)
        except Exception as e:
            print(f"Error extracting links with JavaScript: {e}")
        
        print(f"Found {len(internal_links)} internal pages.")
        
        # Debug: If still no links found, print the page content
        if len(internal_links) == 0:
            print("No links found. Saving page HTML for debugging...")
            with open("notion_debug.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("Debugging HTML saved to notion_debug.html")

        index = []

        for link in internal_links:
            print(f"Scraping: {link}")
            page.goto(link)
            page.wait_for_timeout(8000)  # Wait longer 
            soup = BeautifulSoup(page.content(), "html.parser")
            
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else "Untitled"
            
            # Pass the page title to extract_content for code file naming
            content_blocks = extract_content(soup, title)

            # Generate a filename based on the page title
            file_name = title.lower().replace(" ", "_").replace("/", "_") + ".json"
            
            # Determine which category this page belongs to
            category = determine_category(title, content_blocks)
            # Create the full path for the file
            folder = os.path.join(SAVE_DIR, category)
            save_json(content_blocks, folder, file_name)

            index.append({
                "title": title,
                "path": f"{category}/{file_name}",
                "source_url": link
            })

        # Save the index of all pages
        save_json(index, SAVE_DIR, "index.json")

        browser.close()
        print("Scraping and conversion completed.")

if __name__ == "__main__":
    scrape_notion_wiki()