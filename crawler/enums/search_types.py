from enum import Enum


class SearchType(str, Enum):
    REPOSITORIES = "Repositories"
    ISSUES = "Issues"
    WIKIS = "Wikis"
