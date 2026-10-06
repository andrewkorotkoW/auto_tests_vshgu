"""Причины xfail для подтверждённых дефектов СТЕНДА хелпдеска (не инфраструктуры автотестов) —
подтверждены живыми прогонами на develop после фикса контракта Backpack-форм (t1,
api/endpoints/helpdesk.py/ui/pages/helpdesk_*.py). Вынесено в отдельный модуль, чтобы не
дублировать длинный текст причины в каждом тесте, задетом одним и тем же корневым дефектом.
"""

USER_SEARCH_500_DEFECT_REASON = (
    'Дефект шире описанного в docs/helpdesk_recon.md §5.1: POST /admin/user/search отвечает 500 '
    '(\'Undefined array key "data"\', UserCrudController.php:82) не только на многословную ФИО-строку, '
    'а на любой запрос, не совпадающий с уже проиндексированными сид-пользователями, — воспроизведено '
    'для только что созданного тестового пользователя: полный email, часть email, ФИО одним словом, '
    'даже числовой ID — все варианты дают 500. Поиск по тикетам (другой контроллер) для новых данных '
    'работает нормально — баг локален для UserCrudController::search(). Подтверждено повторно после '
    'фикса контракта Backpack-форм (t1) — поведение не изменилось, дефект не связан с CSRF/Accept.'
)

GROUP_CREATE_JSON_RESPONSE_DEFECT_REASON = (
    'Дефект стенда GroupCrudController::store()/update() (App\\Http\\Controllers\\Admin\\'
    'GroupCrudController.php): при Accept: application/json (нужен, чтобы получать разбираемый '
    '422 JSON на невалидных данных — см. докстринг HelpdeskEndpoint._submit_form) контроллер на '
    'УСПЕШНОМ создании/обновлении группы бросает TypeError "Return value must be of type '
    'Illuminate\\Http\\RedirectResponse, Illuminate\\Http\\JsonResponse returned" (HTTP 500), хотя '
    'сама группа создаётся/обновляется в БД. Воспроизведено стабильно для create/view/update/delete '
    '(все требуют рабочего create_group в предусловии). Шаблоны/заявители/справочники с тем же '
    'Accept-заголовком работают нормально — дефект локален для GroupCrudController.'
)
