import streamlit as st
import os
import base64
from openai import AzureOpenAI
import concurrent.futures
import json
import time

# Set page config at the very beginning
st.set_page_config(page_title="L'Oréal Men Expert Image Analysis", page_icon="🧔")

# Azure OpenAI configuration
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://openai-service-azure-rag-student-account.openai.azure.com/")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
subscription_key = os.getenv("AZURE_OPENAI_KEY", "81ca01fb9209495595887d4c27bfbcf")

# Product suggestions dictionaries
skin_suggestions = {
    "Dry Skin": "L'Oréal Men Expert Hydra Energetic Moisturizer",
    "Oily Skin": "L'Oréal Men Expert Pure Carbon Mattifying Gel",
    "Combination Skin": "L'Oréal Men Expert Hydra Power Water Gel",
    "Sensitive Skin": "L'Oréal Men Expert Hydra Sensitive Cream",
    "Acne-Prone Skin": "L'Oréal Men Expert Pure Carbon Face Wash",
    "Dull Skin": "L'Oréal Men Expert Turbo Booster Brightening Moisturizer",
    "Dark Circles": "L'Oréal Men Expert Hydra Energetic Eye Roll-On",
    "Wrinkles & Aging": "L'Oréal Men Expert Vita Lift Anti-Aging Cream",
    "Hyperpigmentation": "L'Oréal Paris Glycolic Bright Serum",
    "Rough Texture": "L'Oréal Men Expert Pure Carbon Scrub"
}

hair_scalp_suggestions = {
    "Hairfall / Thinning": "L'Oréal Men Expert Full Resist Shampoo",
    "Dandruff / Dry Scalp": "L'Oréal Men Expert Anti-Dandruff Shampoo",
    "Oily Scalp": "L'Oréal Paris Extraordinary Clay Shampoo",
    "Frizzy Hair": "L'Oréal Paris Elvive Smooth Intense Serum",
    "Colored Hair": "L'Oréal Paris Color Protect Shampoo",
    "Curly Hair": "L'Oréal Paris Dream Lengths Curls Leave-in Cream",
    "Greying Hair": "L'Oréal Men Expert One-Twist Hair Color"
}

beard_grooming_suggestions = {
    "Patchy Beard": "L'Oréal Men Expert Barber Club Beard & Hair Oil",
    "Dry & Rough Beard": "L'Oréal Men Expert Barber Club Moisturizer",
    "Beard Dandruff": "L'Oréal Men Expert Beard Wash",
    "Ingrown Hairs": "L'Oréal Men Expert Shaving Gel",
    "Greying Beard": "L'Oréal Men Expert Beard Color"
}

body_care_hygiene_suggestions = {
    "Body Odor": "L'Oréal Men Expert Carbon Protect Deodorant",
    "Dry & Itchy Skin": "L'Oréal Men Expert Hydra Power Shower Gel",
    "Dark Underarms": "L'Oréal Paris White Active Roll-On",
    "Rough Hands & Feet": "L'Oréal Paris Hydra Energetic Hand Cream"
}

# Prompts
SKIN_PROMPT = """
Analyze the given image of a person and comment on their skin attributes:

{
  "Skin Attributes": {
    "Dry Skin": "Lacks moisture, flaky, tight",
    "Oily Skin": "Excess shine, greasy, enlarged pores",
    "Combination Skin": "Oily T-zone, dry cheeks",
    "Sensitive Skin": "Redness, irritation, reactive",
    "Acne-Prone Skin": "Frequent breakouts, clogged pores",
    "Dull Skin": "Lacks glow, uneven tone",
    "Dark Circles": "Under-eye shadows, tired look",
    "Wrinkles & Aging": "Fine lines, sagging, loss of elasticity",
    "Hyperpigmentation": "Dark spots, uneven skin tone",
    "Rough Texture": "Bumpy, uneven, coarse skin"
  }
}

Identify the skin attributes from the above list and answer accordingly, there can also be multiple.

Answer in this JSON format only:
{
  "skin_attributes": [],
  "summary": ""
}
"""

HAIR_PROMPT = """
Analyze the given image of a person and comment on their hair and scalp attributes:

{
  "Hair & Scalp Attributes": {
    "Hairfall / Thinning": "Weak, sparse, excessive shedding",
    "Dandruff / Dry Scalp": "Flaky, itchy, white flakes",
    "Oily Scalp": "Greasy, limp, excess sebum",
    "Frizzy Hair": "Unruly, dry, lacks smoothness",
    "Colored Hair": "Dyed, processed, potential damage",
    "Curly Hair": "Coiled, textured, prone to dryness",
    "Greying Hair": "White strands, aging, pigment loss"
  }
}

Identify the hair and scalp attributes from the above list and answer accordingly, there can also be multiple.

Answer in this JSON format only:
{
  "hair_attributes": [],
  "summary": ""
}
"""

BEARD_PROMPT = """
Analyze the given image of a person and comment on their beard and grooming attributes:

{
  "Beard & Grooming Attributes": {
    "Patchy Beard": "Uneven, sparse, inconsistent growth",
    "Dry & Rough Beard": "Coarse, brittle, lacks moisture",
    "Beard Dandruff": "Flaky, itchy, white particles",
    "Ingrown Hairs": "Bumps, trapped hairs, inflammation",
    "Greying Beard": "White strands, aging, pigment loss"
  }
}

Identify the beard and grooming attributes from the above list and answer accordingly, there can also be multiple.

Answer in this JSON format only:
{
  "beard_attributes": [],
  "summary": ""
}
"""

BODYCARE_PROMPT = """
Analyze the given image of a person and comment on their bodycare and hygiene attributes:

{
  "Body Care & Hygiene Attributes": {
    "Body Odor": "Unpleasant smell, excessive sweating",
    "Dry & Itchy Skin": "Flaky, irritated, moisture loss",
    "Dark Underarms": "Pigmented, uneven skin tone",
    "Rough Hands & Feet": "Calloused, dry, cracked skin"
  }
}

Identify the bodycare and hygiene attributes from the above list and answer accordingly, there can also be multiple.

Answer in this JSON format only:
{
  "bodycare_attributes": [],
  "summary": ""
}
"""

def get_chat_response(input_text, enc_image):
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2024-05-01-preview",
    )
    
    chat_prompt = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are a beauty consultant. You take in image of people and analyse their beauty attributes. These are the beauty attributes that you need to answer from. It can be multiple also, but should be from these categories only. Speak about minimum of 2-3 attributes.\n\n{\n  \"Skin Attributes\": {\n    \"Dry Skin\": \"Lacks moisture, flaky, tight\",\n    \"Oily Skin\": \"Excess shine, greasy, enlarged pores\",\n    \"Combination Skin\": \"Oily T-zone, dry cheeks\",\n    \"Sensitive Skin\": \"Redness, irritation, reactive\",\n    \"Acne-Prone Skin\": \"Frequent breakouts, clogged pores\",\n    \"Dull Skin\": \"Lacks glow, uneven tone\",\n    \"Dark Circles\": \"Under-eye shadows, tired look\",\n    \"Wrinkles & Aging\": \"Fine lines, sagging, loss of elasticity\",\n    \"Hyperpigmentation\": \"Dark spots, uneven skin tone\",\n    \"Rough Texture\": \"Bumpy, uneven, coarse skin\"\n  },\n  \"Hair & Scalp Attributes\": {\n    \"Hairfall / Thinning\": \"Weak, sparse, excessive shedding\",\n    \"Dandruff / Dry Scalp\": \"Flaky, itchy, white flakes\",\n    \"Oily Scalp\": \"Greasy, limp, excess sebum\",\n    \"Frizzy Hair\": \"Unruly, dry, lacks smoothness\",\n    \"Colored Hair\": \"Dyed, processed, potential damage\",\n    \"Curly Hair\": \"Coiled, textured, prone to dryness\",\n    \"Greying Hair\": \"White strands, aging, pigment loss\"\n  },\n  \"Beard & Grooming Attributes\": {\n    \"Patchy Beard\": \"Uneven, sparse, inconsistent growth\",\n    \"Dry & Rough Beard\": \"Coarse, brittle, lacks moisture\",\n    \"Beard Dandruff\": \"Flaky, itchy, white particles\",\n    \"Ingrown Hairs\": \"Bumps, trapped hairs, inflammation\",\n    \"Greying Beard\": \"White strands, aging, pigment loss\"\n  },\n  \"Body Care & Hygiene Attributes\": {\n    \"Body Odor\": \"Unpleasant smell, excessive sweating\",\n    \"Dry & Itchy Skin\": \"Flaky, irritated, moisture loss\",\n    \"Dark Underarms\": \"Pigmented, uneven skin tone\",\n    \"Rough Hands & Feet\": \"Calloused, dry, cracked skin\"\n  }\n}"
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "\n"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{enc_image}"
                    }
                },
                {
                    "type": "text",
                    "text": "\n"
                },
                {
                    "type": "text",
                    "text": input_text
                }
            ]
        }
    ]
    
    completion = client.chat.completions.create(
        model=deployment,
        messages=chat_prompt,
        max_tokens=800,
        temperature=0.25,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False
    )
    
    completion_json = json.loads(completion.to_json())
    return completion_json['choices'][0]['message']['content']

def get_product_suggestions(analysis_results):
    suggestions = {
        "skin": {
            "summary": "",
            "recommendations": []
        },
        "hair": {
            "summary": "",
            "recommendations": []
        },
        "beard": {
            "summary": "",
            "recommendations": []
        },
        "bodycare": {
            "summary": "",
            "recommendations": []
        }
    }
    
    if "skin_attributes" in analysis_results:
        suggestions["skin"]["summary"] = analysis_results.get("skin_summary", "")
        for attribute in analysis_results["skin_attributes"]:
            if attribute in skin_suggestions:
                suggestions["skin"]["recommendations"].append({
                    "concern": attribute,
                    "product": skin_suggestions[attribute]
                })
    
    if "hair_attributes" in analysis_results:
        suggestions["hair"]["summary"] = analysis_results.get("hair_summary", "")
        for attribute in analysis_results["hair_attributes"]:
            if attribute in hair_scalp_suggestions:
                suggestions["hair"]["recommendations"].append({
                    "concern": attribute,
                    "product": hair_scalp_suggestions[attribute]
                })
    
    if "beard_attributes" in analysis_results:
        suggestions["beard"]["summary"] = analysis_results.get("beard_summary", "")
        for attribute in analysis_results["beard_attributes"]:
            if attribute in beard_grooming_suggestions:
                suggestions["beard"]["recommendations"].append({
                    "concern": attribute,
                    "product": beard_grooming_suggestions[attribute]
                })
    
    if "bodycare_attributes" in analysis_results:
        suggestions["bodycare"]["summary"] = analysis_results.get("bodycare_summary", "")
        for attribute in analysis_results["bodycare_attributes"]:
            if attribute in body_care_hygiene_suggestions:
                suggestions["bodycare"]["recommendations"].append({
                    "concern": attribute,
                    "product": body_care_hygiene_suggestions[attribute]
                })
    
    return suggestions

def analyze_prompt(prompt_tuple, encoded_image):
    category_key, prompt_text = prompt_tuple
    response = get_chat_response(prompt_text, encoded_image)
    parsed_response = json.loads(response.strip('```json\n').strip())
    return category_key, parsed_response

def process_image(image):
    encoded_image = base64.b64encode(image.getvalue()).decode('ascii')
    
    prompts = [
        ("skin", SKIN_PROMPT),
        ("hair", HAIR_PROMPT),
        ("beard", BEARD_PROMPT),
        ("bodycare", BODYCARE_PROMPT),
    ]
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_category = {executor.submit(analyze_prompt, p, encoded_image): p[0] for p in prompts}
        results = {}
        for future in concurrent.futures.as_completed(future_to_category):
            category_key = future_to_category[future]
            try:
                category_key, parsed_response = future.result()
                results[category_key] = parsed_response
            except Exception as e:
                st.error(f"Error in {category_key}: {str(e)}")
    
    skin_json = results.get("skin", {"skin_attributes": [], "summary": ""})
    hair_json = results.get("hair", {"hair_attributes": [], "summary": ""})
    beard_json = results.get("beard", {"beard_attributes": [], "summary": ""})
    bodycare_json = results.get("bodycare", {"bodycare_attributes": [], "summary": ""})
    
    TOTAL_SUMMARY = ""
    if skin_json["skin_attributes"]:
        TOTAL_SUMMARY += skin_json["summary"] + " "
    if hair_json["hair_attributes"]:
        TOTAL_SUMMARY += hair_json["summary"] + " "
    if beard_json["beard_attributes"]:
        TOTAL_SUMMARY += beard_json["summary"] + " "
    if bodycare_json["bodycare_attributes"]:
        TOTAL_SUMMARY += bodycare_json["summary"] + " "
    TOTAL_SUMMARY = TOTAL_SUMMARY.strip()
    
    analysis_results = {
        "skin_attributes": skin_json["skin_attributes"],
        "skin_summary": skin_json["summary"],
        "hair_attributes": hair_json["hair_attributes"],
        "hair_summary": hair_json["summary"],
        "beard_attributes": beard_json["beard_attributes"],
        "beard_summary": beard_json["summary"],
        "bodycare_attributes": bodycare_json["bodycare_attributes"],
        "bodycare_summary": bodycare_json["summary"],
        "total_summary": TOTAL_SUMMARY
    }
    
    product_suggestions = get_product_suggestions(analysis_results)
    
    return analysis_results, product_suggestions

# Streamlit UI
st.title("L'Oréal Men Expert Image Analysis")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
submit_button = st.button("Analyze Image")

if uploaded_file is not None and submit_button:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
    st.write("")

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(step, total_steps):
        progress = (step / total_steps) * 100
        progress_bar.progress(int(progress))
        time.sleep(0.5)  # Simulate processing time

    encoded_image = base64.b64encode(uploaded_file.getvalue()).decode('ascii')

    prompts = [
        ("skin", SKIN_PROMPT),
        ("hair", HAIR_PROMPT),
        ("beard", BEARD_PROMPT),
        ("bodycare", BODYCARE_PROMPT),
    ]

    results = {}
    total_steps = len(prompts) + 2  # Analysis steps + product suggestions + final summary
    current_step = 0

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_category = {executor.submit(analyze_prompt, p, encoded_image): p[0] for p in prompts}
        for future in concurrent.futures.as_completed(future_to_category):
            category_key = future_to_category[future]
            try:
                category_key, parsed_response = future.result()
                results[category_key] = parsed_response
                current_step += 1
                status_text.text(f"Analyzing {category_key.capitalize()} Attributes...")
                update_progress(current_step, total_steps)
            except Exception as e:
                st.error(f"Error in {category_key}: {str(e)}")

    skin_json = results.get("skin", {"skin_attributes": [], "summary": ""})
    hair_json = results.get("hair", {"hair_attributes": [], "summary": ""})
    beard_json = results.get("beard", {"beard_attributes": [], "summary": ""})
    bodycare_json = results.get("bodycare", {"bodycare_attributes": [], "summary": ""})

    TOTAL_SUMMARY = ""
    for json_result in [skin_json, hair_json, beard_json, bodycare_json]:
        if json_result.get("summary"):
            TOTAL_SUMMARY += json_result["summary"] + " "
    TOTAL_SUMMARY = TOTAL_SUMMARY.strip()

    analysis_results = {
        "skin_attributes": skin_json["skin_attributes"],
        "skin_summary": skin_json["summary"],
        "hair_attributes": hair_json["hair_attributes"],
        "hair_summary": hair_json["summary"],
        "beard_attributes": beard_json["beard_attributes"],
        "beard_summary": beard_json["summary"],
        "bodycare_attributes": bodycare_json["bodycare_attributes"],
        "bodycare_summary": bodycare_json["summary"],
        "total_summary": TOTAL_SUMMARY
    }

    status_text.text("Generating Product Suggestions...")
    current_step += 1
    update_progress(current_step, total_steps)
    product_suggestions = get_product_suggestions(analysis_results)

    status_text.text("Finalizing Analysis...")
    current_step += 1
    update_progress(current_step, total_steps)

    st.header("Analysis Results")
    st.write(analysis_results["total_summary"])

    st.header("Product Recommendations")

    for category in ["skin", "hair", "beard", "bodycare"]:
        if product_suggestions[category]["recommendations"]:
            st.subheader(f"{category.capitalize()} Care")
            st.write(product_suggestions[category]["summary"])
            for recommendation in product_suggestions[category]["recommendations"]:
                st.write(f"- For {recommendation['concern']}: {recommendation['product']}")

    status_text.text("Analysis Complete!")
    progress_bar.progress(100)
