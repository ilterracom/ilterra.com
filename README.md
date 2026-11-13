# ilterra.com

Статический сайт ILTERRA. Он заменяет прежнюю версию на WordPress: никакого движка,
базы данных и плагинов на сервере, только HTML, CSS и немного JavaScript.
Собирается генератором `build.py` (Python + Jinja2 + Markdown) и публикуется
на GitHub Pages через GitHub Actions.

Главные свойства:

- **Работает на любом домене и в любой подпапке.** Все ссылки между страницами,
  на картинки, стили и скрипты относительные. Домен нигде не прописан.
- **URL старого сайта сохранены.** Путь Markdown-файла в `content/` совпадает с URL:
  `content/products/lumev/index.md` → `/products/lumev/`, `content/fincast/index.md` → `/fincast/`.
  Тег-страницы остались на `/tag/<slug>/`, категории на `/category/<путь>/`.
- **Облако тегов и шкала опыта строятся автоматически** из тегов страниц и файла `data/experience.yaml`.
- **Проверка ссылок при каждой сборке.** Битая внутренняя ссылка или абсолютная ссылка
  на собственный домен роняет сборку в CI.

## Быстрый старт (Docker)

Нужен только Docker.

```bash
docker compose up dev
```

Сайт откроется на <http://localhost:8484> и пересобирается при каждом сохранении файла.
Другой порт: `DEV_PORT=9000 docker compose up dev`.

Разовая сборка в `_site/` с проверкой ссылок:

```bash
docker compose run --rm build
```

Если нужны canonical-ссылки и `sitemap.xml` (в CI это делается автоматически):

```bash
SITE_URL=https://ilterra.com docker compose run --rm build
```

## Структура

```
content/            страницы и посты в Markdown + их картинки (путь = URL)
  index.md          главная: текст приветствия, подпись, фото
  products/         страница /products/ и продукты (Lumev, Stealth Safe, …)
  work-experience/  страница опыта
  <slug>/index.md   посты старого сайта, на тех же адресах
data/
  experience.yaml   шкала опыта (компании, роли, даты)
  categories.yaml   категории (/category/...)
templates/          HTML-шаблоны Jinja2, иконки SVG
static/assets/      CSS, JS, шрифты, логотип, аватар (копируются как есть)
site.yaml           меню, соцсети, реквизиты компании, настройки облака тегов
build.py            генератор сайта
tools/              вспомогательные скрипты (оптимизация картинок)
```

## Как добавить страницу, пост или продукт

Создайте папку, имя которой станет адресом, и в ней `index.md`:

```markdown
---
title: My new product
date: 2026-11-20
type: product            # product | client | article | doc | page
categories: [our-products, our-products/web]
tags: [docker, python]   # попадут в облако тегов на главной
summary: One or two sentences for cards, search and meta description.
cover: cover.jpg         # картинка для карточек (лежит в этой же папке)
policy: https://policies.ilterra.com/my-product/   # необязательно
weight: 50               # необязательно: продукт попадёт в «Current products», порядок по weight
---

## Заголовок

Обычный Markdown. Картинки кладите рядом: ![Скриншот](screen.png)
```

Типы (`type`):

| type      | где показывается |
|-----------|------------------|
| `product` | `/products/` (с `weight` в «Current products», без него в «Earlier projects») |
| `client`  | блок «Clients & case studies» на `/work-experience/` |
| `article` | заметки. Последние посты категории `knowledge-sharing` выводятся на главной в «Behind the Work» |
| `doc`     | дочерний документ: укажите `parent: /products/lumev/`, и он появится в «Guides & documents» родителя |
| `page`    | обычная страница |

Другие поля front matter: `draft: true` (страница не публикуется), `toc: false`
(без оглавления; по умолчанию оно появляется при 3+ заголовках), `updated: YYYY-MM-DD`,
`description` (meta description, если отличается от `summary`).

Внутри Markdown можно писать HTML. Для двух колонок используется разметка, оставшаяся от миграции:

```html
<div class="cols" markdown="1">
<div class="col" markdown="1">

Левая колонка в **Markdown**

</div>
<div class="col" markdown="1">

Правая колонка

</div>
</div>
```

Ссылки внутри сайта пишите от корня (`/products/lumev/`) или относительно страницы.
Генератор сам превратит их в относительные.

## Концепция вёрстки внутренних страниц

Главная повторяет старый сайт. Все остальные страницы (продукты, кейсы, статьи,
гайды, списки) собраны по одной схеме, и новые материалы автоматически в неё попадают:

1. **Шапка страницы** (`templates/partials/hero.html`): хлебные крошки, метка раздела
   (Product / Case study / Guide / DevOps…), заголовок, лид из `summary`, дата, «Updated»,
   время чтения, кнопки из `links:` и обложка `cover` справа.
2. **Тело**: колонка текста до 820 px и липкий сайдбар справа с «On this page»
   (подсвечивает текущий раздел), ссылками на гайды и политику. На телефоне оглавление
   сворачивается в блок над текстом.
3. **Типографика** (`.prose` в `site.css`): заголовки `##` получают оранжевую черту, списки
   оранжевые маркеры, у кода есть кнопка Copy, картинки открываются по клику.
   Высокие скриншоты (высота ≥ 1.6 ширины) автоматически показываются компактным
   «телефоном» с тенью, а файлы с `button`/`badge` в имени выводятся как бейджи App Store.
4. **Внизу**: теги, категории и три похожих материала того же типа.

Кнопки действий в шапке задаются в front matter:

```yaml
links:
  - title: App Store
    url: https://apps.apple.com/...
    kind: appstore     # appstore | web | download | telegram (меняет только иконку)
```

## Облако тегов

Строится из `tags:` всех страниц и `tags:` записей в `data/experience.yaml`.
Размер шрифта зависит от количества упоминаний (шкала 8–22 pt, как в виджете WordPress).
Для каждого тега генерируется страница `/tag/<slug>/` со всеми проектами, клиентами и записями опыта.
Настройки находятся в `site.yaml` → `tag_cloud`.

## Шкала опыта

Записи лежат в `data/experience.yaml`, порядок неважен (сортировка по `start`).
На широких экранах шкала горизонтальная: у каждой записи свой слот, карточки
чередуются сверху и снизу. Если записи не помещаются, появляется горизонтальная
прокрутка со стрелками, и при загрузке шкала открывается на самых свежих записях.
На телефоне шкала вертикальная, новые записи сверху. Поле `page: /mercedes/` делает
компанию ссылкой на кейс.

## Картинки

Новые картинки перед коммитом стоит пропустить через оптимизатор. Он уменьшает всё,
что шире 1600 px, и пережимает тяжёлые файлы, не меняя имён:

```bash
docker compose run --rm tools tools/optimize_images.py content/my-new-page
```

## Деплой на GitHub Pages

1. Запушьте репозиторий на GitHub.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. Каждый push в `main` запускает `.github/workflows/deploy.yml`: сборка, проверка ссылок, публикация.
   Pull request только собирается и проверяется.
4. Свой домен задаётся в **Settings → Pages → Custom domain** (например `ilterra.com`),
   у регистратора нужно прописать DNS-записи GitHub Pages. Файл `CNAME` в репозитории не нужен.

Адрес сайта для canonical-ссылок и `sitemap.xml` CI берёт из настроек Pages.
Чтобы задать его вручную, создайте переменную репозитория `SITE_URL`
(**Settings → Secrets and variables → Actions → Variables**).

### Любой другой хостинг

Соберите `_site/` (`docker compose run --rm build`) и загрузите содержимое папки на любой
статический хостинг (nginx, S3, Netlify, Cloudflare Pages…) в корень или в любую подпапку.
Чтобы смотреть сборку прямо с диска через `file://`, соберите с `--index-links`:
ссылки будут вести на `…/index.html`.

## Что не переносилось

- Политики конфиденциальности, Payment Policy и Service Policy живут на
  <https://policies.ilterra.com>. Ссылки в меню подвала и на страницах продуктов ведут туда.
- WooCommerce-страницы `/shop/`, `/cart/`, `/checkout/`, `/my-account/` были пустыми.
- Пункты меню Services и Pricing вели на `#`. Они закомментированы в `site.yaml`:
  создайте страницу и раскомментируйте пункт.
