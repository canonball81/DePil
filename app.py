import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import re
import uuid

st.set_page_config(page_title="Shopify Product Scraper", page_icon="🛒")
st.title("🛍️ Shopify Product Scraper for DePil.nl")

st.markdown("""
Upload your `sitemap.csv` (with product URLs) and the `shopify_product_template.csv` to generate valid Shopify product imports.
""")

sitemap_file = st.file_uploader("Upload `sitemap.csv`", type="csv")
template_file = st.file_uploader("Upload `shopify_product_template.csv`", type="csv")

def clean_text(text):
    return re.sub(r'\s+', ' ', text.strip())

def extract_variants(soup):
    """Extract variant size and price pairs"""
    options = soup.select("select option")
    variants = []
    for opt in options:
        text = opt.text.strip()
        price_match = re.search(r"€\s?([\d,\.]+)", text)
        price = price_match.group(1).replace(",", ".") if price_match else "0.00"
        label = text.replace(price_match.group(0), "").strip() if price_match else text
        variants.append((label, price))
    return variants if variants else [("Default", "0.00")]

def scrape_product(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html5lib")

        title_tag = soup.find("h1")
        title = clean_text(title_tag.text) if title_tag else "Unknown Product"

        desc_tag = soup.find("div", class_="product-tab-content")
        description = clean_text(desc_tag.text) if desc_tag else ""

        image_tag = soup.find("img", id="main-product-image")
        image_url = "https://depil.nl" + image_tag['src'] if image_tag and "src" in image_tag.attrs else ""

        variants = extract_variants(soup)
        handle = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

        rows = []
        for i, (option_value, price) in enumerate(variants):
            row = {
                "Handle": handle,
                "Title": title,
                "Body (HTML)": description,
                "Vendor": "DePil",
                "Type": "Supplement",
                "Tags": "imported",
                "Published": "TRUE",
                "Option1 Name": "Size",
                "Option1 Value": option_value,
                "Variant Price": price,
                "Variant Inventory Qty": 100,
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Requires Shipping": "TRUE",
                "Image Src": image_url if i == 0 else "",  # only first row gets image
                "Image Alt Text": title,
                "URL": url
            }
            rows.append(row)
        return rows
    except Exception as e:
        st.error(f"❌ Failed to process {url}: {e}")
        return []

if sitemap_file and template_file:
    sitemap_df = pd.read_csv(sitemap_file)
    template_df = pd.read_csv(template_file)

    urls = sitemap_df.iloc[:, 0].dropna().tolist()
    total = len(urls)
    st.success(f"Found {total} product URLs.")

    results = []
    progress = st.progress(0)
    for idx, url in enumerate(urls):
        results.extend(scrape_product(url))
        progress.progress((idx + 1) / total)

    if results:
        result_df = pd.DataFrame(results)

        # Split into batches of 50
        st.subheader("📦 Download Shopify CSVs")
        batch_size = 50
        for i in range(0, len(result_df), batch_size):
            batch_df = result_df.iloc[i:i + batch_size]
            buffer = io.StringIO()
            batch_df.to_csv(buffer, index=False)
            st.download_button(
                label=f"⬇️ Download Batch {i//batch_size + 1} (Products {i + 1}–{min(i + batch_size, len(result_df))})",
                data=buffer.getvalue(),
                file_name=f"shopify_batch_{i//batch_size + 1}.csv",
                mime="text/csv"
            )
    else:
        st.warning("No products were successfully scraped.")
