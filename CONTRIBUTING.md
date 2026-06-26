# Contributing

Thanks for considering contributing! A few guidelines to get started:

- Fork the repository and open a pull request for changes.
- Follow existing code style and add tests for new features or bug fixes.
- For security-related issues, do not open a public issue — contact the maintainers directly (add contact info here).

Development workflow

```bash
# backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest

# frontend
cd frontend
npm install
npm test
```

Review process

- PRs should include a short description and testing instructions.
- Maintain backwards compatibility where possible and document breaking changes.

License and CLA

- Ensure your contributions comply with the project license.
