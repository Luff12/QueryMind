from modules.missing_index_detector import detect_missing_indexes


def generate_index_recommendations():

    candidates = detect_missing_indexes()

    recommendations = []

    for item in candidates:

        table = item["table"]
        column = item["column"]

        recommendations.append(
            {
                "table": table,
                "column": column,
                "reason": item["reason"],
                "sql": item["sql"],
                "benefit": (
                    f"An index on {table}.{column} may improve "
                    "filtering, searching, or JOIN performance "
                    "when the query workload benefits from it."
                ),
            }
        )

    return recommendations


if __name__ == "__main__":

    print("\n========== INDEX RECOMMENDATIONS ==========\n")

    results = generate_index_recommendations()

    if not results:
        print("No index recommendations available.")

    for index, item in enumerate(results, start=1):

        print(f"\nRecommendation {index}")
        print(f"Table: {item['table']}")
        print(f"Column: {item['column']}")
        print(f"Reason: {item['reason']}")
        print(f"Expected benefit: {item['benefit']}")
        print(f"Suggested SQL: {item['sql']}")
        print("-" * 50)
