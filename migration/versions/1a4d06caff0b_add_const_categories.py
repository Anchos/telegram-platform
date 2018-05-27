"""add_const_categories

Revision ID: 1a4d06caff0b
Revises: 022bf3b62746
Create Date: 2018-05-27 21:27:31.237716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a4d06caff0b'
down_revision = '022bf3b62746'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        INSERT INTO category(name) 
        VALUES
            ('Наука и технологии'),
            ('Телеграм'),
            ('Криптовалюты'),
            ('Авто/мото'),
            ('Бизнес и стартапы'),
            ('18+'),
            ('Другое'),
            ('Здоровье и Спорт'),
            ('Игры и приложения'),
            ('Картинки и фото'),
            ('Кино и ТВ'),
            ('Культура и искусство'),
            ('Мода и красота'),
            ('Музыка'),
            ('Новости и СМИ'),
            ('Образование'),
            ('Политика'),
            ('Образование'),
            ('Туризм и активный отдых'),
            ('Работа и карьера'),
            ('Маркетинг'),
            ('Цитаты'),
            ('Юмор и развлечения'),
            ('Дизайн'),
            ('Еда и кулинария');
        """
    )


def downgrade():
    op.execute(
        """
        TRUNCATE TABLE category CASCADE;
        """
    )
