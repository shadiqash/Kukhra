"""
Project-wide DRF pagination classes.

StandardPagePagination
  - Page-number based (clients pass ?page=N)
  - 50 rows per page (override with ?page_size=N, max 200)
  - Response envelope: { count, next, previous, results }
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
