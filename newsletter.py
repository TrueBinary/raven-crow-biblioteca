"""Bloco de inscrição da newsletter (Buttondown).

O formulário faz POST direto para o Buttondown: nenhum e-mail passa pelo Worker do site
nem fica guardado aqui. Sem script de terceiros. Enquanto BUTTONDOWN_USER estiver vazio,
o bloco não aparece em lugar nenhum.
"""
import re
from html import escape

# Nome de usuário público da conta no Buttondown (buttondown.com/<usuário>).
BUTTONDOWN_USER = ""

CSS = (
    ".rc-nl{background:#141013;border:1px solid #4f1418;border-left:6px solid #e42e3b;border-radius:6px;padding:28px;margin:44px 0;color:#f4f1ec}"
    ".rc-nl h2{font:900 clamp(30px,4.4vw,44px)/1 'Barlow Condensed',Impact,sans-serif;text-transform:uppercase;margin:0 0 8px;padding:0;border:0;color:#f4f1ec}"
    ".rc-nl p{margin:0 0 18px;max-width:58ch;color:#ded0ca;font:400 16px/1.6 'DM Sans',system-ui,sans-serif}"
    ".rc-nl-form{display:grid;grid-template-columns:1fr auto;gap:8px 12px;align-items:end;max-width:560px}"
    ".rc-nl-form label{grid-column:1/-1;font:700 13px/1.2 'DM Sans',sans-serif;letter-spacing:.04em;color:#f4f1ec}"
    ".rc-nl-form input{min-width:0;height:48px;padding:0 14px;border:1px solid #8a6f6c;border-radius:6px;background:#0d0e12;color:#f4f1ec;font:500 16px 'DM Sans',sans-serif}"
    ".rc-nl-form input::placeholder{color:#a8a19b}"
    ".rc-nl-form input:focus-visible,.rc-nl-form button:focus-visible{outline:3px solid #ff6b5f;outline-offset:2px}"
    ".rc-nl-form button{height:48px;padding:0 22px;border:0;border-radius:6px;background:#c8202a;color:#fff;font:800 14px/1 'DM Sans',sans-serif;letter-spacing:.05em;text-transform:uppercase;cursor:pointer;white-space:nowrap}"
    ".rc-nl-form button:hover{background:#e0262c}"
    ".rc-nl-form button:active{transform:translateY(1px)}"
    ".rc-nl small{display:block;margin-top:12px;color:#b9b3ad;font:400 13px/1.5 'DM Sans',sans-serif}"
    "@media(max-width:560px){.rc-nl{padding:22px}.rc-nl-form{grid-template-columns:1fr}.rc-nl-form button{width:100%}}"
)


def block(placement: str) -> str:
    """HTML do bloco para um ponto da página (home, artigo, coluna); vazio sem conta configurada."""
    user = BUTTONDOWN_USER.strip()
    if not user:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", user):
        raise ValueError("BUTTONDOWN_USER inválido: " + repr(user))
    pid = "rc-nl-email-" + re.sub(r"[^a-z0-9-]", "", placement.lower())
    return (
        '<style>' + CSS + '</style>'
        '<section class="rc-nl" aria-labelledby="' + pid + '-t">'
        '<h2 id="' + pid + '-t">O Corvo no seu e-mail</h2>'
        '<p>As principais notícias e análises do Raven Crow, direto na sua caixa de entrada. Sem spam.</p>'
        '<form class="rc-nl-form" action="https://buttondown.com/api/emails/embed-subscribe/' + escape(user, quote=True) + '" '
        'method="post" target="_blank" rel="noopener noreferrer">'
        '<label for="' + pid + '">Seu e-mail</label>'
        '<input id="' + pid + '" type="email" name="email" required autocomplete="email" inputmode="email" maxlength="254" placeholder="voce@exemplo.com">'
        '<button type="submit">Assinar</button>'
        '</form>'
        '<small>Você recebe um e-mail para confirmar. Cancelar é um clique em qualquer edição. '
        'O cadastro fica no Buttondown, serviço que envia a newsletter.</small>'
        '</section>'
    )
