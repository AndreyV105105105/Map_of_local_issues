import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone
from users.models import CustomUser
from issues.models import Issue, Category, IssuePhoto


@pytest.fixture
def test_user_citizen(db):
    """Фикстура: обычный гражданин (не верифицирован по email)."""
    user = CustomUser.objects.create_user(
        email="citizen@example.com",
        password="StrongPass123!",
        first_name="Анна",
        last_name="Кузнецова",
        patronymic="Сергеевна",
        role="citizen",
        phone_number="+79991234567",
        department=None,
        email_verified=True,  # для удобства большинства тестов
    )
    return user


@pytest.fixture
def test_user_official(db):
    """Фикстура: должностное лицо."""
    user = CustomUser.objects.create_user(
        email="official@example.com",
        password="StrongPass123!",
        first_name="Дмитрий",
        last_name="Петров",
        role="official",
        department="Управление ЖКХ",
        email_verified=True,
    )
    return user


@pytest.fixture
def test_user_unverified(db):
    """Фикстура: пользователь с неверифицированным email (для тестов верификации)."""
    user = CustomUser.objects.create_user(
        email="unverified@example.com",
        password="pass123",
        role="citizen",
        email_verified=False,
    )
    return user


@pytest.fixture
def test_category(db):
    """Фикстура: категория «Дороги»."""
    category, _ = Category.objects.get_or_create(
        name="Дороги",
        slug="roads",
        description="Ямы, разметка, знаки",
    )
    return category


@pytest.fixture
def test_issue(test_user_citizen, test_category):
    """Фикстура: открытое обращение от гражданина."""
    issue = Issue.objects.create(
        title="Яма на перекрёстке Ленина и Мира",
        description="Глубокая яма, опасна для машин и пешеходов.",
        location=Point(69.0223, 61.0066, srid=4326),  # Ханты-Мансийск
        address="ул. Ленина, 10",
        category="roads",
        reporter=test_user_citizen,
        status=Issue.STATUS_OPEN,
    )
    return issue


@pytest.fixture
def test_issue_in_progress(test_user_citizen, test_user_official):
    """Фикстура: обращение в работе (назначено официальному лицу)."""
    issue = Issue.objects.create(
        title="Не работает светофор",
        description="Светофор на ул. Южной не работает уже неделю.",
        location=Point(69.0300, 61.0100, srid=4326),
        address="ул. Южная, 5",
        category="lighting",
        reporter=test_user_citizen,
        assigned_to=test_user_official,
        status=Issue.STATUS_IN_PROGRESS,
    )
    return issue


@pytest.fixture
def test_photo_uploaded(tmp_path, test_issue):
    """Фикстура: загруженное фото (имитация)."""
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile

    # Создаём временное изображение
    image_path = tmp_path / "test_photo.jpg"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(image_path, "JPEG")

    with open(image_path, "rb") as f:
        photo_file = SimpleUploadedFile(
            name="test_photo.jpg",
            content=f.read(),
            content_type="image/jpeg"
        )

    photo = IssuePhoto.objects.create(
        issue=test_issue,
        image=photo_file,
        caption="Фото ямы"
    )
    return photo