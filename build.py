import os
import json
import re

## TODOS:
# - Underline animations for highlighted elements in a pastel color that looks good in grayscale
# - Custom highlights for each skill in a unique pastel color
# - Expandable descriptions upon hovering

## Load the resume data
with open("./resume.json", "r") as file:
    resume = json.load(file)

## Load the index template
with open("./index_src.html", "r") as file:
    index = file.read()

## Load the component templates
component_files = os.listdir("./components")
component_names = [name[:-len(".html")] for name in component_files]
components = []

for component_file in component_files:
    with open(f"./components/{component_file}") as file:
        components.append(file.read())

## Infill a template with the resume data
def infill(template, data):
    for key, value in data.items():
        if isinstance(value, str):
            template = template.replace(f"$${key}$$", value)
    return template

## Infill the top level placeholders in the index template
index = infill(index, resume)

## Replace the component placeholders with the corresponding infilled templates
for component_name, component in zip(component_names, components):
    assert component_name in resume, f"Component {component_name} not found in resume data"
    assert isinstance(resume[component_name], list), f"Component {component_name} must be a list"

    infilled_components = []
    for value in resume[component_name]:
        infilled_components.append(infill(component, value))

    index = index.replace(f"%%{component_name}%%", "\n".join(infilled_components))

## Highlight any text between **text** by nesting it in <span class='highlight'>
index = re.sub(r"\*\*(.*?)\*\*", r"<span class='highlight'>\1</span>", index)

## Replace any links in format [text](url) with <a href="$$url$$" target="_blank">text</a>
index = re.sub(r"\[(.*?)\]\((.*?)\)", r"<a href='\2' target='_blank'>\1</a>", index)

## Save the complete index file
with open("./index.html", "w") as file:
    file.write(index)