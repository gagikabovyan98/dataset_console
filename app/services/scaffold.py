# app/services/scaffold.py

def build_scaffold_code(pairs: list[tuple[str, str]], default_limit: int = 1000) -> str:
    lines: list[str] = []
    lines.append("#!/usr/bin/env python3")
    lines.append("")
    lines.append("def main():")
    if not pairs:
        lines.append("    pass")
    else:
        for i, (title, _table) in enumerate(pairs, start=1):
            safe_title = (title or f"dataset {i}").replace("\n", " ").strip()
            lines.append(f"    # Dataset {i}: {safe_title}")
            lines.append(f"    # variable: ds{i}")
            lines.append("")
        lines.append("    pass")
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append("    main()")
    return "\n".join(lines)
