from playwright.sync_api import Page, expect


def test_open_page_and_read_title(page: Page):
    page.goto("https://anme.city")

    expect(page).to_have_title("Login")

    login_element = page.get_by_role("heading")

    expect(login_element).to_have_text("Login Here")
