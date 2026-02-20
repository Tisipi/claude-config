Read spec.md, prompt_plan.md, and other relevant project files. Create a Graphviz `.dot` file that visually represents the project architecture, components, dependencies, and data flows.

The diagram should clearly show:
- Major components and modules
- Relationships and dependencies between components
- Data flow between systems
- Layers or domains if applicable

Validate the generated `.dot` file by rendering it to SVG:
```bash
dot -Tsvg project.dot -o project.svg
```

Fix any syntax errors if validation fails. Save both `project.dot` and `project.svg` to the project root.
