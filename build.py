import os

component_files = os.listdir("./components")
component_names = [name[:-len(".html")] for name in component_files]
components = []

for component_file in component_files:
    with open(f"./components/{component_file}") as file:
        components.append(file.read())

with open("./index_src.html", "r") as file:
    index = file.read()

while True:
    old_index = index
    for component_name, component in zip(component_names, components):
        index = index.replace(f"$${component_name}$$", component)

    if index == old_index:
        break

with open("./index.html", "w") as file:
    file.write(index)