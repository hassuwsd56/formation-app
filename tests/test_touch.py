"""フォーメーション管理：タッチ操作・シート・保存の回帰テスト

実行: "/c/Users/skyio/anaconda3/python.exe" tests/test_touch.py [アプリのフォルダ（既定はこのリポジトリ）]
"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/webapp-test/scripts"))
from cdp import Browser, Checker, serve

HERE = os.path.dirname(os.path.abspath(__file__))
app_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..")
URL = serve(app_dir) + "index.html"
KEY = "formationApp_v1"
OUT = os.path.join(os.environ.get("TEMP", HERE), "formation-test-shots")

names = ["テスト一郎", "テスト二郎", "テスト三郎", "テスト四郎", "テスト五郎", "テスト六郎", "テスト七郎", "テスト八郎", "テスト九郎"]
players = [{"id": f"p{i}", "name": n, "number": str(i + 1)} for i, n in enumerate(names)]
pos = [[50, 92], [30, 72], [70, 72], [16, 49], [50, 52], [84, 49], [50, 25]]
s1 = [{"x": x, "y": y, "p": f"p{i}"} for i, (x, y) in enumerate(pos)]
s2 = [dict(s, p="p7" if i == 3 else "p8" if i == 6 else s["p"]) for i, s in enumerate(s1)]
SEED = {KEY: {"version": 1, "mode": "sociiti", "tab": "field", "players": players, "formations": [],
              "plans": {"sociiti": {"cur": "b", "periods": [
                  {"id": "a", "name": "前半", "minutes": 15, "slots": s1},
                  {"id": "b", "name": "後半", "minutes": 15, "slots": s2}]}}}}

ck = Checker()
with Browser() as b:
    b.open(URL, seed=SEED)
    data = lambda: b.js(f"JSON.parse(localStorage.getItem('{KEY}'))")
    slot = lambda i: data()["plans"]["sociiti"]["periods"][1]["slots"][i]
    plans_json = lambda: b.js(f"JSON.stringify(JSON.parse(localStorage.getItem('{KEY}')).plans)")
    body_top = lambda: b.js("document.body.style.top")

    with ck.step("表示"):
        ck.check("コマが7個表示される", b.js("document.querySelectorAll('#field g.piece').length") == 7)
        ck.check("交代（OUT/IN）が2件表示される", b.js("document.querySelectorAll('.card .sub').length") == 2)
        b.screenshot(os.path.join(OUT, "field.png"), full=True)

    with ck.step("スクロール"):
        b.js("scrollTo(0,0)"); b.pump(0.2)
        _, py = b.center(".pername", scroll=False)
        b.swipe(200, py, 200, py - 160)
        ck.check("[対照] コート外のスワイプでスクロールできる", b.js("scrollY") > 50, f"scrollY={b.js('scrollY')}")
        b.js("scrollTo(0,0)"); b.pump(0.2)
        before = plans_json()
        fx, fy = b.js("(()=>{const r=document.querySelector('#field').getBoundingClientRect();return [r.left+r.width*0.05, r.top+r.height*0.62]})()")
        on_piece = b.js(f"!!document.elementFromPoint({fx},{fy}).closest('g.piece')")
        b.swipe(fx, fy, fx, fy - 250)
        ck.check("コートの空き部分をスワイプでスクロールできる", b.js("scrollY") > 50 and not on_piece,
                 f"scrollY={b.js('scrollY')} 開始点がコマ上={on_piece}")
        ck.check("コートのスクロールでコマは動かない", plans_json() == before)

    with ck.step("ドラッグ"):
        b.js("scrollTo(0,0)"); b.pump(0.2)
        y_before = slot(4)["y"]
        px, py = b.center("g.piece[data-slot='4'] circle:nth-of-type(3)", scroll=False)
        b.swipe(px, py, px, py - 120)
        ck.check("コマをドラッグで動かせる", slot(4)["y"] < y_before - 10, f"y {y_before} -> {slot(4)['y']}")
        ck.check("ドラッグ中はページがスクロールしない", b.js("scrollY") == 0)
        ck.check("ドラッグ後にシートは開かない", not b.exists("#sheet"))

    with ck.step("コマのシート"):
        b.js("scrollTo(0,150)"); b.pump(0.2)
        px, py = b.center("g.piece[data-slot='2'] circle:nth-of-type(3)", scroll=False)
        b.tap(px, py)
        ck.check("コマのタップでシートが開いたまま", b.exists("#sheet"))
        ck.check("シート表示中は背面が固定される", b.js("document.body.style.position") == "fixed")
        b.swipe(195, 120, 195, 400); b.swipe(195, 400, 195, 100)
        ck.check("暗い部分をなぞっても背面は動かない", body_top() == "-150px", body_top())
        ck.check("暗い部分をなぞってもシートは閉じない", b.exists("#sheet"))
        sx, sy = b.center(".sheet", scroll=False)
        b.swipe(sx, sy + 150, sx, sy - 100)
        ck.check("シート内のスクロールで背面は動かない", body_top() == "-150px", body_top())
        b.screenshot(os.path.join(OUT, "sheet.png"))
        before = plans_json()
        b.tap(195, 60)
        ck.check("暗い部分のタップでシートが閉じる", not b.exists("#sheet"))
        ck.check("閉じると元のスクロール位置に戻る", b.js("scrollY") == 150, f"scrollY={b.js('scrollY')}")
        ck.check("背面のデータは変化していない", plans_json() == before)

    with ck.step("ベンチから交代"):
        b.js("scrollTo(0,0)"); b.pump(0.2)
        b.tap_el(".bench[data-pid='p3']")
        ck.check("ベンチの選手タップで交代シートが開く", b.exists("#sheet"))
        b.tap_el("#sheet [data-act='swapIn'][data-slot='1']")
        ck.check("交代するとその位置にベンチ選手が入る", slot(1)["p"] == "p3", slot(1)["p"])

    with ck.step("フォーメーションシート"):
        b.tap_el("[data-act='formations']")
        ck.check("フォーメーションシートが開く", b.exists("#sheet"))
        top0 = body_top()
        sx, sy = b.center(".sheet", scroll=False)
        b.swipe(sx, sy + 150, sx, sy - 150)
        ck.check("フォーメーションシートのスクロールで背面は動かない", body_top() == top0 and b.js("scrollY") == 0, f"{top0} -> {body_top()}")
        b.tap_el("#sheet [data-act='applyFormation'][data-src='preset']")
        ck.check("適用でシートが閉じ、背面の固定が解除される", not b.exists("#sheet") and b.js("document.body.style.position") == "")

    with ck.step("交代計画と保存"):
        b.tap_el("#tabs [data-tab='plan']")
        ck.check("交代計画の表に選手9人＋人数行が並ぶ", b.js("document.querySelectorAll('tbody tr').length") == 10)
        b.screenshot(os.path.join(OUT, "plan.png"), full=True)
        b.reload()
        ck.check("再読み込み後も交代計画タブとデータが残る", b.js("!!document.querySelector('table')") and slot(1)["p"] == "p3")

    with ck.step("アイコン・manifest"):
        ck.check("manifest とアイコンが読み込める", b.js("""(async()=>{
            const m = await (await fetch(document.querySelector('link[rel=manifest]').href)).json();
            const urls = [document.querySelector('link[rel=apple-touch-icon]').href, ...m.icons.map(i => new URL(i.src, location.href).href)];
            const rs = await Promise.all(urls.map(u => fetch(u)));
            return rs.every(r => r.ok && r.headers.get('content-type').startsWith('image/'));
        })()"""))

    ck.check("JSエラーなし", not b.errors, b.errors)

print("screenshots:", OUT)
sys.exit(ck.summary())
