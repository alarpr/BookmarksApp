from bs4 import BeautifulSoup, Tag
from typing import List, Tuple, Optional


def parse_bookmarks_html(html: str) -> List[Tuple[List[str], str, str]]:
    """
    Parse Safari/Netscape Bookmarks HTML which typically uses <DL>/<DT>/<H3> for folders
    and <DT><A ...> for links. Returns list of (path, title, href) where path is folder list.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: List[Tuple[List[str], str, str]] = []

    def folder_name_for_dl(dl: Tag) -> Optional[str]:
        """Find the H3 whose associated DL contains this dl (robust across <p> wrappers)."""
        for h3 in dl.find_all_previous("h3"):
            next_dl = h3.find_next("dl")
            if isinstance(next_dl, Tag) and (next_dl is dl or dl in next_dl.descendants):
                return h3.get_text(strip=True)
        return None

    def build_path_for_anchor(a: Tag) -> List[str]:
        path: List[str] = []
        dl = a.find_parent("dl")
        while isinstance(dl, Tag):
            name = folder_name_for_dl(dl)
            if name:
                path.insert(0, name)
            dl = dl.find_parent("dl")
        return path

    for a in soup.find_all("a"):
        if not a.has_attr("href"):
            continue
        title = a.get_text(strip=True) or a["href"]
        href = a["href"]
        path = build_path_for_anchor(a)
        results.append((path, title, href))

    return results


