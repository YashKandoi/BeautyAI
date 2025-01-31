import os  
import base64
from openai import AzureOpenAI  
import concurrent.futures
import json

endpoint = "https://openai-service-azure-rag-student-account.openai.azure.com/"
deployment = "gpt-4o"
subscription_key = "81ca01fb9209495595887d4c27bfbcf6"

skin_suggestions = {
    "Dry Skin": "L’Oréal Men Expert Hydra Energetic Moisturizer",
    "Oily Skin": "L’Oréal Men Expert Pure Carbon Mattifying Gel",
    "Combination Skin": "L’Oréal Men Expert Hydra Power Water Gel",
    "Sensitive Skin": "L’Oréal Men Expert Hydra Sensitive Cream",
    "Acne-Prone Skin": "L’Oréal Men Expert Pure Carbon Face Wash",
    "Dull Skin": "L’Oréal Men Expert Turbo Booster Brightening Moisturizer",
    "Dark Circles": "L’Oréal Men Expert Hydra Energetic Eye Roll-On",
    "Wrinkles & Aging": "L’Oréal Men Expert Vita Lift Anti-Aging Cream",
    "Hyperpigmentation": "L’Oréal Paris Glycolic Bright Serum",
    "Rough Texture": "L’Oréal Men Expert Pure Carbon Scrub"
}

hair_scalp_suggestions = {
    "Hairfall / Thinning": "L’Oréal Men Expert Full Resist Shampoo",
    "Dandruff / Dry Scalp": "L’Oréal Men Expert Anti-Dandruff Shampoo",
    "Oily Scalp": "L’Oréal Paris Extraordinary Clay Shampoo",
    "Frizzy Hair": "L’Oréal Paris Elvive Smooth Intense Serum",
    "Colored Hair": "L’Oréal Paris Color Protect Shampoo",
    "Curly Hair": "L’Oréal Paris Dream Lengths Curls Leave-in Cream",
    "Greying Hair": "L’Oréal Men Expert One-Twist Hair Color"
}

beard_grooming_suggestions = {
    "Patchy Beard": "L’Oréal Men Expert Barber Club Beard & Hair Oil",
    "Dry & Rough Beard": "L’Oréal Men Expert Barber Club Moisturizer",
    "Beard Dandruff": "L’Oréal Men Expert Beard Wash",
    "Ingrown Hairs": "L’Oréal Men Expert Shaving Gel",
    "Greying Beard": "L’Oréal Men Expert Beard Color"
}

body_care_hygiene_suggestions = {
    "Body Odor": "L’Oréal Men Expert Carbon Protect Deodorant",
    "Dry & Itchy Skin": "L’Oréal Men Expert Hydra Power Shower Gel",
    "Dark Underarms": "L’Oréal Paris White Active Roll-On",
    "Rough Hands & Feet": "L’Oréal Paris Hydra Energetic Hand Cream"
}



SKIN_PROMPT = """ 
Analyze the given image of a person and comment on their skin  attributes:

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
  "summary": "" # Don't include suggestions in summary, include only the details of the problem!
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
  "summary": "" # Don't include suggestions in summary, include only the details of the problem!
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
  "summary": "" # Don't include suggestions in summary, include only the details of the problem!
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
  "summary": "" # Don't include suggestions in summary, include only the details of the problem!
}
"""

def get_chat_response(input_text, enc_image):
    client = AzureOpenAI(  
        azure_endpoint=endpoint,  
        api_key=subscription_key,  
        api_version="2024-05-01-preview",  
    )
    
    # Prepare the chat prompt 
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
    
    # Generate the completion  
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
    
    # Convert the completion to JSON and parse it
    completion_json = json.loads(completion.to_json())
    
    # Extract and return the content from the message JSON body
    return completion_json['choices'][0]['message']['content']


def get_product_suggestions(analysis_results):
    """Get product suggestions based on the analysis results"""
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
    
    # Get skin suggestions
    if "skin_attributes" in analysis_results:
        suggestions["skin"]["summary"] = analysis_results.get("skin_summary", "")
        for attribute in analysis_results["skin_attributes"]:
            if attribute in skin_suggestions:
                suggestions["skin"]["recommendations"].append({
                    "concern": attribute,
                    "product": skin_suggestions[attribute]
                })
    
    # Get hair suggestions
    if "hair_attributes" in analysis_results:
        suggestions["hair"]["summary"] = analysis_results.get("hair_summary", "")
        for attribute in analysis_results["hair_attributes"]:
            if attribute in hair_scalp_suggestions:
                suggestions["hair"]["recommendations"].append({
                    "concern": attribute,
                    "product": hair_scalp_suggestions[attribute]
                })
    
    # Get beard suggestions
    if "beard_attributes" in analysis_results:
        suggestions["beard"]["summary"] = analysis_results.get("beard_summary", "")
        for attribute in analysis_results["beard_attributes"]:
            if attribute in beard_grooming_suggestions:
                suggestions["beard"]["recommendations"].append({
                    "concern": attribute,
                    "product": beard_grooming_suggestions[attribute]
                })
    
    # Get bodycare suggestions
    if "bodycare_attributes" in analysis_results:
        suggestions["bodycare"]["summary"] = analysis_results.get("bodycare_summary", "")
        for attribute in analysis_results["bodycare_attributes"]:
            if attribute in body_care_hygiene_suggestions:
                suggestions["bodycare"]["recommendations"].append({
                    "concern": attribute,
                    "product": body_care_hygiene_suggestions[attribute]
                })
    
    return suggestions

# Create a function for parallel execution
def analyze_prompt(prompt_tuple):
    category_key, prompt_text = prompt_tuple
    response = get_chat_response(prompt_text, encoded_image)
    # Strip code fences if the response is in code-block format
    parsed_response = json.loads(response.strip('```json\n').strip())
    return category_key, parsed_response


# Encode the image once; avoid re-encoding multiple times
IMAGE_PATH = "image2.png"
encoded_image = base64.b64encode(open(IMAGE_PATH, 'rb').read()).decode('ascii')

# Prepare your prompts in a list
prompts = [
    ("skin", SKIN_PROMPT),
    ("hair", HAIR_PROMPT),
    ("beard", BEARD_PROMPT),
    ("bodycare", BODYCARE_PROMPT),
]

# Run the analyses in parallel
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_category = {executor.submit(analyze_prompt, p): p for p in prompts}
    results = {}
    for future in concurrent.futures.as_completed(future_to_category):
        category_key = future_to_category[future]
        try:
            category_key, parsed_response = future.result()
            results[category_key] = parsed_response
        except Exception as e:
            # Handle exceptions if needed
            print(f"Error in {category_key}: {str(e)}")

# Use the results
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

print("Complete Analysis:")
print(TOTAL_SUMMARY)

# Construct your analysis_results dict
analysis_results = {
    "skin_attributes": skin_json.get("skin_attributes", []),
    "skin_summary": skin_json.get("summary", ""),
    "hair_attributes": hair_json.get("hair_attributes", []),
    "hair_summary": hair_json.get("summary", ""),
    "beard_attributes": beard_json.get("beard_attributes", []),
    "beard_summary": beard_json.get("summary", ""),
    "bodycare_attributes": bodycare_json.get("bodycare_attributes", []),
    "bodycare_summary": bodycare_json.get("summary", "")
}

# Then proceed with get_product_suggestions and printing logic as before
product_suggestions = get_product_suggestions(analysis_results)

print("Analysis and Recommendations:\n")
categories = {
    "skin": "Skin Care",
    "hair": "Hair Care",
    "beard": "Beard Care",
    "bodycare": "Body Care"
}

for category_key, category_name in categories.items():
    category_data = product_suggestions[category_key]
    if category_data["summary"] or category_data["recommendations"]:
        print(f"{category_name} Analysis:")
        print(category_data["summary"])
        if category_data["recommendations"]:
            print(f"\nRecommended {category_name} Products:")
            for rec in category_data["recommendations"]:
                print(f"\nConcern: {rec['concern']}")
                print(f"Recommended Product: {rec['product']}")
        print("\n" + "="*50 + "\n")