"""
A manager has full write access to /users/, but must not be able to mint or
become a superuser. Only a superuser may grant the superuser role or edit a
superuser account.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


@pytest.fixture
def manager(db):
    return User.objects.create_user(username='esc_mgr', password='x', role=Role.MANAGER)


@pytest.fixture
def superuser(db):
    return User.objects.create_user(username='esc_root', password='x', role=Role.SUPERUSER)


def api(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_manager_cannot_create_superuser(manager):
    r = api(manager).post('/api/users/', {
        'username': 'sneaky', 'password': 'longenough1', 'role': Role.SUPERUSER,
    }, format='json')
    assert r.status_code == 400
    assert not User.objects.filter(username='sneaky').exists()


def test_manager_cannot_self_escalate(manager):
    r = api(manager).patch(f'/api/users/{manager.pk}/', {'role': Role.SUPERUSER}, format='json')
    assert r.status_code == 400
    manager.refresh_from_db()
    assert manager.role == Role.MANAGER


def test_manager_cannot_edit_superuser(manager, superuser):
    r = api(manager).patch(f'/api/users/{superuser.pk}/', {'phone': '9800000000'}, format='json')
    assert r.status_code == 400
    superuser.refresh_from_db()
    assert superuser.phone == ''


def test_manager_can_create_ordinary_roles(manager):
    r = api(manager).post('/api/users/', {
        'username': 'newcashier', 'password': 'longenough1', 'role': Role.CASHIER,
    }, format='json')
    assert r.status_code == 201


def test_superuser_can_create_superuser(superuser):
    r = api(superuser).post('/api/users/', {
        'username': 'root2', 'password': 'longenough1', 'role': Role.SUPERUSER,
    }, format='json')
    assert r.status_code == 201
