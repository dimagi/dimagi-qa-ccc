"""Submit History report access (CCCT-2671).

Answering every question on the device only proves half of the Connect Survey
cases. TC-BRD-004, TC-CAL-006 and TC-KWD-005 ask for the other half - that the
completed survey actually reached HQ - and that evidence lives in Submit
History.

This reads the report's JSON endpoint instead of scraping the rendered table.
It is the same data the page shows (HQ's SubmitHistory is a tabular report also
served as JSON under /reports/json/<slug>/), and it avoids depending on the
table's DOM. The request goes through the Playwright context, so it reuses the
session the test already logged in with rather than authenticating a second
way.

Submissions are attributed to the Connect user id, not the PersonalID mobile
worker - a submission searched for by mobile worker finds nothing even though
the row is sitting there, which is what made these cases look blocked.
"""

import datetime
import html
import re

# Submit History renders the time in the viewing account's timezone and labels
# it. Comparing a naive timestamp against a UTC cutoff would silently match the
# wrong row - five and a half hours of wrong, for an Indian account - so the
# label is parsed rather than ignored, and an unknown one is an error instead of
# a guess.
_TZ_OFFSETS = {
    "UTC": datetime.timedelta(0),
    "GMT": datetime.timedelta(0),
    "IST": datetime.timedelta(hours=5, minutes=30),
}


class CCHQReportsPage:
    def __init__(self, page, config):
        self.page = page
        url = config.get("cchq_url")
        match = re.match(r"^(https?://[^/]+)/a/([^/]+)/", url)
        assert match, f"Could not read origin and domain out of cchq_url {url!r}"
        self.origin, self.domain = match.group(1), match.group(2)

    def _submit_history_rows(self, limit):
        url = (
            f"{self.origin}/a/{self.domain}/reports/json/submit_history/"
            f"?iDisplayStart=0&iDisplayLength={limit}"
        )
        response = self.page.request.get(url)
        assert response.status == 200, (
            f"Submit History returned {response.status} for {url} - the report moved, "
            "or this session is not logged in to that project space"
        )
        return response.json()["aaData"]

    @staticmethod
    def _parse_time(raw):
        """'Aug 18, 2026 05:46:03 UTC' -> aware UTC datetime."""
        match = re.match(r"(\w+ \d{1,2}, \d{4} \d{1,2}:\d{2}:\d{2})\s*(\w+)?", raw.strip())
        if not match:
            return None
        try:
            stamp = datetime.datetime.strptime(match.group(1), "%b %d, %Y %H:%M:%S")
        except ValueError:
            return None
        label = (match.group(2) or "UTC").upper()
        assert label in _TZ_OFFSETS, (
            f"Submit History reported an unhandled timezone {label!r} in {raw!r}. Add it to "
            "_TZ_OFFSETS - guessing an offset would silently compare against the wrong instant."
        )
        return (stamp - _TZ_OFFSETS[label]).replace(tzinfo=datetime.timezone.utc)

    def recent_submissions(self, limit=25):
        submissions = []
        for view_link, submitted_by, time_str, path in self._submit_history_rows(limit):
            form_id = re.search(r"/reports/form_data/([\w-]+)/", view_link)
            submissions.append(
                {
                    "form_id": form_id.group(1) if form_id else None,
                    "submitted_by": html.unescape(submitted_by),
                    "time": time_str,
                    "submitted_at": self._parse_time(time_str),
                    "path": html.unescape(path),
                }
            )
        return submissions

    def find_submission(self, user_id, form_path_contains, after, limit=25):
        """Most recent submission by `user_id` for a form whose breadcrumb
        contains `form_path_contains`, submitted after the aware datetime
        `after`. None if there is no such row.

        `after` is not optional on purpose. Without it a previous run's
        submission satisfies the assertion and the test passes while proving
        nothing, which is the exact failure mode these cases were stuck on.
        """
        for submission in self.recent_submissions(limit):
            if user_id not in submission["submitted_by"]:
                continue
            if form_path_contains.lower() not in submission["path"].lower():
                continue
            if submission["submitted_at"] is None or submission["submitted_at"] < after:
                continue
            return submission
        return None

    def wait_for_submission(self, user_id, form_path_contains, after, timeout=180_000, poll=10_000):
        """find_submission, retried - the survey's last answer and the form
        landing in the report are not the same instant."""
        waited = 0
        while True:
            found = self.find_submission(user_id, form_path_contains, after)
            if found or waited >= timeout:
                return found
            self.page.wait_for_timeout(poll)
            waited += poll
