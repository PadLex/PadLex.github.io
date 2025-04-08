import os
import json
import re
import random

random.seed(42)

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


## Replace any links in format [text](url) with <a href="$$url$$" target="_blank">text</a>
index = re.sub(r"\[(.*?)\]\((.*?)\)", r"<a href='\2' target='_blank'>\1</a>", index)


## Add highlighting and underlining markers
colors = {"c1": "250, 223, 161", "c2": "242, 198, 223", "c3": "197, 222, 242", "c4": "218, 204, 239", "c5": "201, 228, 223"}
marker_colors = []
def highlight(match):
    marker_colors.append(colors[match.group(1)])
    return f"<mark class='marker{len(marker_colors)-1}'>{match.group(2)}</mark>"
index = re.sub(r"\*\*\*\{(" + "|".join(colors) + r")\}\((.*?)\)\*\*\*", highlight, index)

def underline(match):
    marker_colors.append(colors[match.group(1)])
    return f"<mark class='marker{len(marker_colors)-1} underline'>{match.group(2)}</mark>"
index = re.sub(r"\*\*\{(" + "|".join(colors) + r")\}\((.*?)\)\*\*", underline, index)

## Save the complete index file
with open("./index.html", "w") as file:
    file.write(index)



## Generate marker.css from marker_src.css so that each marker is unique
with open("marker_src.txt", "r") as file:
    marker_src = file.read()

marker_styles = ""
times = []
for i in range(len(marker_colors)):
    marker = marker_src.replace("$$id$$", f"marker{i}")
    marker = marker.replace("$$color$$", marker_colors[i])

    marker = marker.replace("$$a1$$", str(random.randint(1, 3) / 10))
    marker = marker.replace("$$a2$$", str(random.randint(5, 9) / 10))
    marker = marker.replace("$$a3$$", str(random.randint(1, 3) / 10))
    marker = marker.replace("$$a4$$", str(random.randint(5, 9) / 10))

    marker = marker.replace("$$p1$$", str(random.randint(1, 6)))
    marker = marker.replace("$$p2$$", str(random.randint(94, 100)))

    r1 = random.randint(2, 9) / 10
    marker = marker.replace("$$r1$$", str(r1))
    marker = marker.replace("$$r2$$", str(1 - r1 + random.randint(-1, 1) / 10))

    times.append(random.randint(4, 7) / 10)
    marker = marker.replace("$$time$$", str(times[-1]))

    marker_styles += marker


with open("./marker.css", "w") as file:
    file.write(marker_styles)

