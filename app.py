import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import re
from urllib.parse import urlparse

st.title("🛍️ Shopify Product Scraper")

# Upload sitemap CSV
sitemap_file = st.file_uploader("Upload sitemap.csv", type="csv")
template_file = st.file_uploader("Upload Shopify template CSV", type="csv")

if sitemap_file and template_file:
    sitemap_df = pd.read_csv(sitemap_file)
    base_template = pd.read_csv(template_file)
    urls = sitemap_df.iloc[:, 0].dropna().tolist()
    st.success(f"Found {len(urls)} product URLs.")

    products = []
    for url in urls:
        try:
            res = requests.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            
            title = soup.find("h1").text.strip()
            description = soup.find("div", class_="product-tab-content").get_text(strip=True)
            image_tag = soup.find("img", {"id": "main-product-image"})
            image_url = image_tag['src'] if image_tag else ''
            variations = soup.select("select option")  # Assume select dropdown for size

            handle = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')

            for var in variations:
                variant_text = var.text.strip()
                price = re.search(r"\€([\d\.,]+)", variant_text)
                size = re.sub(r"\€.*", "", variant_text).strip()
                price_val = price.group(1).replace(',', '.') if price else ''

                row = {
                    "Handle": handle,
                    "Title": title,
                    "Body (HTML)": description,
                    "Variant Price": price_val,
                    "Image Src": image_url,
                    "Option1 Value": size,
                    "Tags": "imported",
                    "Published": "TRUE",
                    "Variant Inventory Qty": 100,
                    "Variant Inventory Policy": "deny",
                    "Variant Fulfillment Service": "manual",
                    "Variant Requires Shipping": "TRUE",
                    "Image Alt Text": title,
                    "URL": url
                }
                products.append(row)

        except Exception as e:
            st.warning(f"Failed to process {url}: {e}")

    # Create DataFrame
    shopify_df = pd.DataFrame(products)

    # Split into batches of 50
    batch_size = 50
    batches = [shopify_df[i:i + batch_size] for i in range(0, len(shopify_df), batch_size)]

    for i, batch in enumerate(batches):
        buffer = io.StringIO()
        batch.to_csv(buffer, index=False)
        st.download_button(
            label=f"Download Batch {i+1} (CSV)",
            data=buffer.getvalue(),
            file_name=f"shopify_products_batch_{i+1}.csv",
            mime="text/csv"
        )
