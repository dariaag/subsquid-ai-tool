"""InspectorToolSpec."""

import requests

    
def introspect_schema() -> str:
        """
        Introspects the subgraph and summarizes its schema into textual categories.

        Returns:
            str: A textual summary of the introspected subgraph schema.
        """
        introspection_query = """
        query {
            __schema {
                types {
                    kind
                    name
                    description
                    enumValues {
                        name
                    }
                    fields {
                        name
                        args {
                            name
                        }
                        type {
                            kind
                            name
                            ofType {
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        url = 'https://squid.subsquid.io/swaps-squid/v/v1/graphql'
   

        response = requests.post(url, json={"query": introspection_query})
        #print(response.text)
        data = response.json()
        print(data["data"])
        if "data" in data:
            result = data["data"]
            processed_subgraph = _process_subgraph(result)
            print(subgraph_to_text(processed_subgraph))
            return subgraph_to_text(processed_subgraph)
        else:
            print("Error during introspection.")
            return "Error during introspection."
def _process_subgraph( result: dict) -> dict:
        """
        Processes the introspected subgraph schema into categories based on naming conventions.

        Args:
            result (dict): Introspected schema result from the GraphQL query.

        Returns:
            dict: A processed representation of the introspected schema, categorized into specific entity queries, list entity queries, and other entities.
        """
        processed_subgraph = {
            "specific_entity_queries": {},
            "list_entity_queries": {},
            "other_entities": {},
        }
        for type_ in result["__schema"]["types"]:
            if type_["name"].startswith("__"):
                continue  # Skip meta entities

            entity_name = type_["name"]
            fields, args_required = _get_fields(type_)
            if fields:
                # Determine category based on naming convention
                if entity_name.endswith("s") and not args_required:
                    processed_subgraph["list_entity_queries"][entity_name] = fields
                elif not entity_name.endswith("s") and args_required:
                    processed_subgraph["specific_entity_queries"][entity_name] = fields
                else:
                    processed_subgraph["other_entities"][entity_name] = fields

        return processed_subgraph
def subgraph_to_text( subgraph: dict) -> str:
        """
        Converts a processed subgraph representation into a textual summary based on entity categories.

        Args:
            subgraph (dict): A processed representation of the introspected schema, categorized into specific entity queries, list entity queries, and other entities.

        Returns:
            str: A textual summary of the processed subgraph schema.
        """
        sections = [
            (
                "Specific Entity Queries (Requires Arguments)",
                "These queries target a singular entity and require specific arguments (like an ID) to fetch data.",
                """
            {
                entityName(id: "specific_id") {
                    fieldName1
                    fieldName2
                    ...
                }
            }
            """,
                subgraph["specific_entity_queries"],
            ),
            (
                "List Entity Queries (Optional Arguments)",
                "These queries fetch a list of entities. They don't strictly require arguments but often accept optional parameters for filtering, sorting, and pagination.",
                """
            {
                entityNames(first: 10, orderBy: "someField", orderDirection: "asc") {
                    fieldName1
                    fieldName2
                    ...
                }
            }
            """,
                subgraph["list_entity_queries"],
            ),
            (
                "Other Entities",
                "These are additional entities that may not fit the conventional singular/plural querying pattern of subgraphs.",
                "",
                subgraph["other_entities"],
            ),
        ]

        result_lines = []
        for category, desc, example, entities in sections:
            result_lines.append(format_section(category, desc, example, entities))

        return "\n".join(result_lines)
def _get_fields( type_):
        """
        Extracts relevant fields and their details from a given type within the introspected schema.

        Args:
            type_ (dict): A type within the introspected schema.

        Returns:
            tuple: A tuple containing a list of relevant fields and a boolean indicating if arguments are required for the fields.
        """
        fields = []
        args_required = False
        for f in type_.get("fields") or []:
            if f["name"] != "__typename" and not (
                f["name"].endswith("_filter")
                or f["name"].endswith("_orderBy")
                or f["name"].islower()
            ):
                field_info = {"name": f["name"]}

                # Check for enum values
                if "enumValues" in f["type"] and f["type"]["enumValues"]:
                    field_info["enumValues"] = [
                        enum_val["name"] for enum_val in f["type"]["enumValues"]
                    ]

                fields.append(field_info)
                if f.get("args") and len(f["args"]) > 0:
                    args_required = True
                if f.get("type") and f["type"].get("fields"):
                    subfields, sub_args_required = _get_fields(f["type"])
                    fields.extend(subfields)
                    if sub_args_required:
                        args_required = True
        return fields, args_required
def format_section(
         category: str, description: str, example: str, entities: dict
    ) -> str:
        """
        Formats a given section of the subgraph introspection result into a readable string format.

        Args:
            category (str): The category name of the entities.
            description (str): A description explaining the category.
            example (str): A generic GraphQL query example related to the category.
            entities (dict): Dictionary containing entities and their fields related to the category.

        Returns:
            str: A formatted string representation of the provided section data.
        """
        section = [
            f"Category: {category}",
            f"Description: {description}",
            "Generic Example:",
            example,
            "\nDetailed Breakdown:",
        ]

        for entity, fields in entities.items():
            section.append(f"  Entity: {entity}")
            for field_info in fields:
                field_str = f"    - {field_info['name']}"
                if "enumValues" in field_info:
                    field_str += (
                        f" (Enum values: {', '.join(field_info['enumValues'])})"
                    )
                section.append(field_str)
            section.append("")  # Add a blank line for separation

        section.append("")  # Add another blank line for separation between sections
        return "\n".join(section)
