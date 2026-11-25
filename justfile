run:
  uv run ./manage.py tailwind runserver

test:
  uv run ./manage.py test

format:
  uv run ruff format .
  uv run ruff check --fix .
  uv run djlint --reformat --warn .

check:
  uv run ruff check . 
  uv run djlint --lint .
  uv run mypy .

# Sets the version in pyproject.toml, commits it and pushes it with a matching tag, which publishes the release.
release version:
  uv version {{version}}
  git commit -m "Release {{version}}" pyproject.toml uv.lock
  git tag {{version}}
  git push --atomic origin HEAD {{version}}
