"""
User admin hardening (review findings H3 / M1):
 - DELETE deactivates instead of hard-deleting, and a manager cannot remove
   a superuser account.
 - Passwords are manageable after creation: admin reset + self-service change.
 - Password events revoke outstanding refresh tokens.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role, User


@pytest.fixture
def superuser(db):
    return User.objects.create_user(username='root', password='rootpass123', role=Role.SUPERUSER)


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='mgr', password='mgrpass123', role=Role.MANAGER)


@pytest.fixture
def cashier(db):
    return User.objects.create_user(username='till', password='tillpass123', role=Role.CASHIER)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
def test_manager_cannot_delete_superuser(manager, superuser):
    res = client_for(manager).delete(f'/api/users/{superuser.pk}/')
    assert res.status_code == 403
    superuser.refresh_from_db()
    assert superuser.is_active


@pytest.mark.django_db
def test_superuser_can_deactivate_superuser(superuser):
    other = User.objects.create_user(username='root2', password='rootpass123', role=Role.SUPERUSER)
    res = client_for(superuser).delete(f'/api/users/{other.pk}/')
    assert res.status_code == 204
    other.refresh_from_db()
    assert not other.is_active


@pytest.mark.django_db
def test_delete_deactivates_instead_of_removing(manager, cashier):
    res = client_for(manager).delete(f'/api/users/{cashier.pk}/')
    assert res.status_code == 204
    cashier.refresh_from_db()
    assert not cashier.is_active   # record kept — ledger FKs stay intact


@pytest.mark.django_db
def test_cannot_deactivate_self(manager):
    res = client_for(manager).delete(f'/api/users/{manager.pk}/')
    assert res.status_code == 400
    manager.refresh_from_db()
    assert manager.is_active


@pytest.mark.django_db
def test_manager_resets_cashier_password(manager, cashier):
    res = client_for(manager).post(
        f'/api/users/{cashier.pk}/set-password/', {'password': 'fresh-till-9'}, format='json'
    )
    assert res.status_code == 200
    cashier.refresh_from_db()
    assert cashier.check_password('fresh-till-9')


@pytest.mark.django_db
def test_manager_cannot_reset_superuser_password(manager, superuser):
    res = client_for(manager).post(
        f'/api/users/{superuser.pk}/set-password/', {'password': 'takeover-99'}, format='json'
    )
    assert res.status_code == 403
    superuser.refresh_from_db()
    assert superuser.check_password('rootpass123')


@pytest.mark.django_db
def test_weak_password_rejected(manager, cashier):
    res = client_for(manager).post(
        f'/api/users/{cashier.pk}/set-password/', {'password': 'short'}, format='json'
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_self_service_password_change(cashier):
    res = client_for(cashier).post('/api/users/change-password/', {
        'current_password': 'tillpass123', 'new_password': 'my-new-till-7',
    }, format='json')
    assert res.status_code == 200
    cashier.refresh_from_db()
    assert cashier.check_password('my-new-till-7')


@pytest.mark.django_db
def test_password_change_requires_correct_current(cashier):
    res = client_for(cashier).post('/api/users/change-password/', {
        'current_password': 'wrong', 'new_password': 'my-new-till-7',
    }, format='json')
    assert res.status_code == 400
    cashier.refresh_from_db()
    assert cashier.check_password('tillpass123')


@pytest.mark.django_db
def test_password_reset_revokes_refresh_tokens(manager, cashier):
    refresh = RefreshToken.for_user(cashier)
    client_for(manager).post(
        f'/api/users/{cashier.pk}/set-password/', {'password': 'fresh-till-9'}, format='json'
    )
    res = APIClient().post('/api/auth/token/refresh/', {'refresh': str(refresh)}, format='json')
    assert res.status_code == 401


@pytest.mark.django_db
def test_deactivation_revokes_refresh_tokens(manager, cashier):
    refresh = RefreshToken.for_user(cashier)
    client_for(manager).delete(f'/api/users/{cashier.pk}/')
    res = APIClient().post('/api/auth/token/refresh/', {'refresh': str(refresh)}, format='json')
    assert res.status_code == 401
