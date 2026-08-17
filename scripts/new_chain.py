# -*- coding: utf-8 -*-
"""new_chain.py — генератор новой сети для ComboPizzaSushiMCP.

Использование:
    python scripts/new_chain.py my_chain "Моя Сеть" https://example.com [--city Воронеж]

Аргументы:
    chain_id  — идентификатор (только [a-z0-9_])
    name      — отображаемое имя сети
    url       — базовый URL
    --city    — город (по умолчанию "Воронеж")
"""

import sys
import os
import re
import json

# ---------------------------------------------------------------------------
# Парсинг аргументов
# ---------------------------------------------------------------------------


def parse_args(argv):
    """Разобрать sys.argv: chain_id, name, url, --city."""
    args = argv[1:]  # skip script name
    if len(args) < 3:
        print("Ошибка: нужно 3 аргумента: chain_id name url [--city город]",
              file=sys.stderr)
        sys.exit(1)

    chain_id = args[0]
    name = args[1]
    url = args[2]
    city = "Воронеж"

    i = 3
    while i < len(args):
        if args[i] == "--city" and i + 1 < len(args):
            city = args[i + 1]
            i += 2
        else:
            print(f"Ошибка: неизвестный аргумент '{args[i]}'", file=sys.stderr)
            sys.exit(1)

    # Валидация chain_id
    if not re.match(r'^[a-z0-9_]+$', chain_id):
        print(
            f"Ошибка: chain_id '{chain_id}' содержит недопустимые символы. "
            "Разрешены только [a-z0-9_].",
            file=sys.stderr,
        )
        sys.exit(1)

    return chain_id, name, url, city


# ---------------------------------------------------------------------------
# Шаблон файла парсера
# ---------------------------------------------------------------------------

PARSER_TEMPLATE = """\
# -*- coding: utf-8 -*-
\"\"\"{name}.py — парсер {name}.

Проще: python scripts/new_chain.py {chain_id} \\"{name}\\" {url}
\"\"\"

from combo_mcp.chains.base import ChainParser, chain, ChainUnavailable
from combo_mcp import config as mcp_config
from combo_mcp import http_client


@chain("{chain_id}")
class {class_name}Parser(ChainParser):
    \"\"\"Парсер {name}.\"\"\"

    id = "{chain_id}"
    name = "{name}"
    city = "{city}"
    url = "{url}"
    description = "Описание новой сети доставки"
    needs_playwright = False
    # category_map: сырая категория меню -> группа комбо
    # (pizza/rolls/sushi/sets/noodles/snacks/desserts/drinks/sauces/other)
    category_map = {{
        # "Сырая категория": "pizza",
        # "Другая категория": "rolls",
    }}

    def parse(self):
        \"\"\"Распарсить меню {name}.

        URL и таймауты берутся из config.get_chain(chain_id).
        \"\"\"
        chain_cfg = mcp_config.get_chain(self.id)
        url = chain_cfg.get("url", self.url)

        # TODO: загрузить и распарсить меню
        raise ChainUnavailable(
            f"Парсер для {{self.id}} не реализован. URL: {{url}}"
        )

    def parse_extra(self) -> dict:
        \"\"\"Доп. информация о сети: доставка, лояльность, акции.\"\"\"
        return {{}}
"""


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------


def main():
    """Создать файл парсера и запись в chains_config.json."""
    chain_id, name, url, city = parse_args(sys.argv)

    # Проверка: файл уже существует
    chain_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "combo_mcp", "chains", f"{chain_id}.py"
    )
    if os.path.exists(chain_file):
        print(f"Ошибка: файл {chain_file} уже существует.", file=sys.stderr)
        sys.exit(1)

    # Проверка: id уже в реестре
    try:
        from combo_mcp.chains.base import _CHAIN_REGISTRY
        if chain_id in _CHAIN_REGISTRY:
            print(
                f"Ошибка: chain_id '{chain_id}' уже зарегистрирован.",
                file=sys.stderr,
            )
            sys.exit(1)
    except ImportError:
        pass

    # Генерация класса
    class_name = "".join(w.capitalize() for w in chain_id.split("_"))
    template = PARSER_TEMPLATE.format(
        name=name, class_name=class_name,
        chain_id=chain_id, url=url, city=city,
    )

    # Запись файла
    os.makedirs(os.path.dirname(chain_file), exist_ok=True)
    with open(chain_file, "w", encoding="utf-8") as f:
        f.write(template)

    # Добавление записи в chains_config.json
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "chains_config.json"
    )
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {"chains": {}}

    config.setdefault("chains", {})[chain_id] = {
        "url": url,
        "enabled": True,
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    # Чек-лист
    print(f"Сеть '{name}' ({chain_id}) создана!")
    print()
    print("Чек-лист:")
    print("  1) Реализовать метод parse() в combo_mcp/chains/{chain_id}.py")
    print("  2) Заполнить category_map (маппинг категорий -> группы комбо)")
    print("  3) Запустить: .venv\\Scripts\\python.exe scripts\\autotest.py")
    print("  4) По желанию: добавить estimated_weights, translations, parse_extra")


if __name__ == "__main__":
    main()
