from playwright.sync_api import sync_playwright
import random
errors=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=r'C:/Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    ctx=b.new_context(viewport={'width':1080,'height':640})
    pg=ctx.new_page()
    pg.on('pageerror',lambda e: errors.append(str(e)))
    pg.goto('http://127.0.0.1:8080/',wait_until='networkidle')
    pg.wait_for_timeout(800)

    # click user center icon
    pg.locator('.user-center-icon').click(force=True)
    pg.wait_for_timeout(400)
    print('=== panel opened ===')
    print('overlay open:', pg.evaluate("document.querySelector('.la-overlay').classList.contains('la-open')"))
    print('tabs:', pg.evaluate("""() => [...document.querySelectorAll('.la-tab')].map(e=>e.textContent)"""))
    pg.screenshot(path='auth_login.png')

    # register
    print('\n=== register ===')
    pg.locator('.la-tab[data-mode="register"]').first.click()
    pg.wait_for_timeout(200)
    uname='testuser'+str(random.randint(1000,9999))
    pg.locator('.la-user-input').fill(uname)
    pg.locator('.la-nick-input').fill('测试用户')
    pg.locator('.la-email-input').fill('test@example.com')
    pg.locator('.la-pass-input').fill('password123')
    pg.locator('.la-pass2-input').fill('password123')
    pg.locator('.la-submit').click()
    pg.wait_for_timeout(900)
    print('msg:', pg.evaluate("document.querySelector('.la-msg').textContent"))
    print('logged in view (has logout):', pg.locator('.la-logout').count())
    print('nick shown:', pg.evaluate("""() => {const e=document.querySelector('.la-nick'); return e?e.textContent:''}"""))
    pg.screenshot(path='auth_loggedin.png')

    # reload - session persistence
    print('\n=== reload persistence ===')
    pg.reload(wait_until='networkidle')
    pg.wait_for_timeout(700)
    pg.locator('.user-center-icon').click(force=True)
    pg.wait_for_timeout(400)
    print('still logged in (logout btn):', pg.locator('.la-logout').count())
    print('nick:', pg.evaluate("""() => {const e=document.querySelector('.la-nick'); return e?e.textContent:''}"""))

    # change password
    print('\n=== change password ===')
    pg.locator('.la-changepw').click()
    pg.wait_for_timeout(150)
    pg.locator('.la-oldpw').fill('password123')
    pg.locator('.la-newpw').fill('newpassword456')
    pg.locator('.la-pw-submit').click()
    pg.wait_for_timeout(600)
    print('msg:', pg.evaluate("document.querySelector('.la-msg').textContent"))

    # logout
    print('\n=== logout ===')
    pg.locator('.la-logout').click()
    pg.wait_for_timeout(500)
    print('login view back:', pg.locator('.la-submit').count())

    # login again with new password
    print('\n=== login new password ===')
    pg.locator('.la-user-input').fill(uname)
    pg.locator('.la-pass-input').fill('newpassword456')
    pg.locator('.la-submit').click()
    pg.wait_for_timeout(700)
    print('msg:', pg.evaluate("document.querySelector('.la-msg').textContent"))
    print('logged in:', pg.locator('.la-logout').count())

    print('\nERRORS:',len(errors)); [print(' ',e[:150]) for e in errors[:5]]
    b.close()
