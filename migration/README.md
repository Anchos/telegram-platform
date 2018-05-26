# Migration project

## Installation

```bash
~cd migration
~pip install requirements.txt
```

That would install Alembic and it's main dependency - SQLAlchemy

## Usage
### Migrate
If you need to just upgrade to latest version just run: 
```bash
alembic upgrade head
```
If you need to upgrade to specific revision:
```bash
alembic upgrade 022
```
Where 022 is a prefix of revision 022bf3b62746

### Write your own migration

Firsly, modify `migration/models.py` file, add new fields, alter tables, etc
Then run:
```bash
alembic revision --autogenerate -m "added some fancy fields"
```
Remember to use `--autogenerate` option. That would compare existing database
to current models stored in `models.py`

If you want to generate empty revision file, run:
```bash
alembic revision -m "added some fancy fields"
```
And write migrations by yourself