from playwright.sync_api import Page, expect


def test_wrong_login(page: Page):
    page.goto("https://anme.city")

    expect(page).to_have_title("Login")

    login_element = page.get_by_role("heading")

    expect(login_element).to_have_text("Login Here")

    # Type "blabla" into username input

    inputs = page.query_selector_all("input")

    [username_input, password_input] = inputs[0], inputs[1]

    username_input.fill("blabla")
    password_input.fill("blabla")

    page.click("input[type=submit]")

    # Expect "Username or Password incorrect" to be present
    text_el = page.get_by_text("Username or Password incorrect")

    expect(text_el).to_be_visible()
