import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

text_intro = """\
# Data Cleaning, Categorization and Visualization

This notebook processes the raw scraped product data. 
It performs the following steps:
1. **Load Data**: Imports JSON files containing the scraped products.
2. **Remove Duplicates**: Drops rows with identical properties.
3. **Categorize Data**: Extracts Brand Name and Product Type using regular expressions and heuristics on the title and description.
4. **Data Polishing**: Applies pandas styling to give the data a better visual representation.
"""

code_imports = """\
import pandas as pd
import glob
import os
import re
import json

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', 100)
"""

code_load_data = """\
# Load all JSON files in the raw data directory
data_dir = '../data/raw/'
all_files = glob.glob(os.path.join(data_dir, "*.json"))

data = []
for file in all_files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            content = json.load(f)
            data.extend(content)
    except Exception as e:
        print(f"Error loading {file}: {e}")

df = pd.DataFrame(data)
print(f"Total rows loaded: {len(df)}")
df.head()
"""

text_dedup = """\
## Remove Duplicate Data
We will drop exact duplicate rows (where data in all columns are identical) to ensure our dataset is clean.
"""

code_dedup = """\
# Drop exact duplicates (where all columns are equal)
initial_len = len(df)
df = df.drop_duplicates()
print(f"Removed {initial_len - len(df)} exact duplicate rows.")

print(f"Total rows after deduplication: {len(df)}")
"""

text_categorize = """\
## Categorize Data: Brand and Product Type

You can configure the list of **Brand Names** and the mapping of **Product Types** to keywords.
These configured lists will be used to automatically detect categories based on the product titles and descriptions.
"""

code_categorize = """\
# ==============================================================
# CONFIGURATION: Add or remove brands and types here
# ==============================================================

# List your target brands here (lowercase)
TARGET_BRANDS = [
    'nike', 'adidas', 'puma', 'reebok', 'under armour', 
    'vans', 'converse', 'new balance', 'korean', 'ms', 
    'cl', 'gucci', 'prada', 'louis vuitton'
]

# Map product categories to their respective keywords (lowercase)
TARGET_CATEGORIES = {
    'Shoes': ['shoe', 'sneaker', 'boot', 'sandal', 'heel', 'footwear', 'fly-knit', 'knit'],
    'Handbags': ['bag', 'handbag', 'purse', 'tote', 'wallet', 'backpack', 'clutch'],
    'Clothing': ['shirt', 't-shirt', 'jacket', 'pant', 'jeans', 'dress', 'hoodie', 'sweater', 'coat', 'top'],
    'Accessories': ['watch', 'belt', 'sunglasses', 'hat', 'cap', 'jewelry', 'necklace', 'bracelet', 'ring']
}

# ==============================================================

def extract_brand(title):
    title_lower = str(title).lower()
    for brand in TARGET_BRANDS:
        if brand in title_lower:
            return brand.title()
    return 'Unknown Brand'

def extract_type(title, description):
    text = (str(title) + ' ' + str(description)).lower()
    
    for category, keywords in TARGET_CATEGORIES.items():
        if any(keyword in text for keyword in keywords):
            return category
    return 'Other'

# Apply the functions to create new columns
df['Brand'] = df['title'].apply(extract_brand)
df['Category'] = df.apply(lambda row: extract_type(row.get('title', ''), row.get('description', '')), axis=1)

# Rearrange columns for better readability
cols = list(df.columns)
if 'Brand' in cols and 'Category' in cols:
    cols.insert(1, cols.pop(cols.index('Brand')))
    cols.insert(2, cols.pop(cols.index('Category')))
    df = df[cols]

df[['title', 'Brand', 'Category']].head(10)
"""

text_style = """\
## Give More Look to Data

We apply Pandas styling to format the presentation of our cleaned DataFrame. We will highlight the prices, apply custom background colors to different categories, and truncate long descriptions.
"""

code_style = """\
# Function to color categories differently
def highlight_category(val):
    color_map = {
        'Shoes': 'background-color: #e6f2ff; color: #004080',
        'Handbags': 'background-color: #ffe6e6; color: #800000',
        'Clothing': 'background-color: #e6ffe6; color: #004d00',
        'Accessories': 'background-color: #fff2e6; color: #804000',
        'Other': 'background-color: #f2f2f2; color: #333333'
    }
    return color_map.get(val, '')

# Format the price column
def format_price(val):
    try:
        return f"Rs. {float(val):,.2f}"
    except:
        return val

# Select a subset of data to display
display_df = df.head(15).copy()

# Shorten descriptions for display purposes
if 'description' in display_df.columns:
    display_df['description'] = display_df['description'].apply(
        lambda x: str(x)[:80] + '...' if len(str(x)) > 80 else x
    )

# Apply styles
styled_df = (display_df.style
             .map(highlight_category, subset=['Category'])
             .format({'price': format_price})
             .set_properties(**{'text-align': 'left'})
             .set_table_styles([
                 dict(selector='th', props=[('text-align', 'center'), ('background-color', '#404040'), ('color', 'white'), ('font-size', '14px')]),
                 dict(selector='td', props=[('font-size', '13px'), ('border', '1px solid #d9d9d9')])
             ])
             .set_caption("Cleaned and Categorized Product Data"))

styled_df
"""

code_save = """\
# Function to save the cleaned and processed data
def save_data_to_csv(dataframe, output_dir='../data/processed/', filename='cleaned_products.csv'):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    dataframe.to_csv(output_path, index=False)
    print(f"Dataframe with {len(dataframe)} rows successfully saved to: {output_path}")
    return output_path

# Execute the save function
saved_path = save_data_to_csv(df)
"""

nb['cells'] = [
    nbf.v4.new_markdown_cell(text_intro),
    nbf.v4.new_code_cell(code_imports),
    nbf.v4.new_code_cell(code_load_data),
    nbf.v4.new_markdown_cell(text_dedup),
    nbf.v4.new_code_cell(code_dedup),
    nbf.v4.new_markdown_cell(text_categorize),
    nbf.v4.new_code_cell(code_categorize),
    nbf.v4.new_markdown_cell(text_style),
    nbf.v4.new_code_cell(code_style),
    nbf.v4.new_code_cell(code_save)
]

output_notebook = '/home/omindu/Documents/Python/scraping-platform/notebooks/data_cleaning_and_processing.ipynb'
with open(output_notebook, 'w') as f:
    nbf.write(nb, f)

print(f"Notebook successfully created at {output_notebook}")
