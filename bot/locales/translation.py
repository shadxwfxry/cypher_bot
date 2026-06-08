TRANSLATIONS = {
    "ru": {
        "welcome": (
            "🌳 Добро пожаловать в бота “Cypher Market”\n\n"
            "⚠️ Перед использованием ознакомьтесь с правилами сервиса.\n\n"
            "🔥 Поставки автоматически публикуются в нашем канале в течение всего дня и регулярные апдейты тут.\n\n"
            "🤓 Support - @sup_cypher\n\n"
            "🚀 Мы приглашаем к сотрудничеству новых поставщиков, подробности в поддержке."
        ),
        "btn_accounts": "💎 Аккаунты",
        "btn_documents": "📁 Документы",
        "btn_self_reg": "⚙️ Self-Reg",
        "btn_fullz": "🪪 FULLZ",
        "btn_lookup": "🔍 Пробив",
        "btn_profile": "👤 Профиль",
        "btn_rules": "📜 Правила",
        "btn_updates": "📢 Обновления",
        "btn_support": "🤝 Помощь",
        "btn_toggle_lang": "English 🇬🇧",
        "admin_panel_welcome": (
            "👑 <b>Панель управления Cypher Bot</b>\n\n"
            "Добро пожаловать, Администратор. Пожалуйста, выберите функцию управления из меню ниже:"
        ),
        "admin_btn_stats": "📊 Статистика",
        "admin_btn_search": "🔍 Поиск юзера",
        "admin_btn_maintenance": "⚙️ Тех. работы",
        "admin_btn_edit_texts": "📝 Настройка текстов",
        "admin_btn_broadcast": "📢 Рассылка",
        "admin_btn_close": "🔙 Закрыть",
        
        "profile_text": (
            "<b>👤 Ваш профиль Cypher</b>\n\n"
            "• <b>Telegram ID:</b> <code>{tg_id}</code>\n"
            "• <b>Никнейм:</b> @{username}\n"
            "• <b>Логин на сайте:</b> <code>{site_login}</code>\n"
            "• <b>Дата регистрации:</b> {reg_date}\n\n"
            "💳 <b>Баланс:</b> <code>${balance:.2f}</code>\n"
            "🛍️ <b>Количество покупок:</b> <code>{purchases_count}</code>\n"
            "💰 <b>Сумма покупок:</b> <code>${purchases_sum:.2f}</code>"
        ),
        
        "btn_deposit": "💳 Пополнить баланс",
        "btn_my_purchases": "🛍️ Мои покупки",
        "btn_my_deposits": "📥 Мои пополнения",
        "btn_link_account": "🔗 Привязать аккаунт",
        "btn_account_linked_active": "✅ Аккаунт привязан ({login})",
        "btn_menu": "🔙 Меню",
        "btn_lang": "🌐 Сменить язык / Change Language",
        
        "lang_switched": "Язык успешно изменен на Русский! 🇷🇺",
        
        "link_blocked_warn": (
            "⚠️ <b>Внимание! Автопривязка заблокирована.</b>\n\n"
            "У вас есть средства на балансе бота (<code>${balance:.2f}</code>) или история покупок.\n\n"
            "Для безопасности ваших данных автопривязка отключена. "
            "Пожалуйста, свяжитесь с администратором @{support_user}, чтобы перенести ваш баланс на сайт.\n\n"
            "<i>Перед этим обязательно нажмите <b>Мои покупки -> Export all</b>, чтобы сохранить локальную историю покупок!</i>"
        ),
        
        "link_prompt": "📝 Пожалуйста, введите ваш хэш-пароль с сайта для привязки аккаунта:",
        "link_success": "🎉 <b>Успешно!</b> Ваш Telegram-аккаунт привязан к логину <b>{login}</b> на сайте.",
        "link_failed": "❌ <b>Ошибка!</b> Неверный хэш-пароль или аккаунт уже привязан к другому пользователю.",
        "link_cancel": "Привязка аккаунта отменена.",
        
        "select_crypto": "💳 <b>Пополнение баланса</b>\n\nВыберите криптовалюту для совершения платежа:",
        "crypto_invoice_text": (
            "💵 <b>Пополнение через {crypto}</b>\n\n"
            "Для оплаты отправьте монеты на следующий кошелек:\n"
            "<code>{address}</code>\n\n"
            "⚠️ <b>Минимальная сумма:</b> <code>15 USDT</code> (или эквивалент).\n"
            "{fee_warning}\n\n"
            "<i>Зачисление происходит автоматически после получения подтверждений сети.</i>"
        ),
        "fee_usdt_warning": "💡 <b>Комиссия:</b> при депозите от 15 до 100 USDT комиссия составляет <b>5 USDT</b>. При депозите от 100 USDT комиссия — <b>0 USDT</b>.",
        "fee_other_warning": "💡 Комиссия сети оплачивается отправителем.",
        
        "payment_success_msg": "🎉 <b>Ваш баланс успешно пополнен!</b>\n\n• <b>Сумма:</b> {amount} {currency}\n• <b>Эквивалент:</b> ${usd_equiv:.2f}\n• <b>Метод:</b> {method}\n\nСпасибо за покупку!",
        
        "purchases_title": "🛍️ <b>Ваши последние покупки (до 10):</b>\n\n{purchases_list}",
        "purchases_empty": "У вас пока нет покупок.",
        "purchases_item_format": "• {date} - <b>{product}</b>: ${amount:.2f}",
        "btn_export_all": "📥 Export all (История за 3 мес.)",
        
        "deposits_title": "📥 <b>Ваши последние пополнения (до 10):</b>\n\n{deposits_list}",
        "deposits_empty": "У вас пока нет пополнений баланса.",
        "deposits_item_format": "• {date} - {amount} {currency} (${usd:.2f}) via {method}",
        
        "export_queued": "⏳ <b>Ваш запрос на экспорт истории добавлен в очередь!</b>\nВоркер обрабатывает файлы последовательно. Вы получите текстовый файл в этом чате в течение нескольких минут.",
        "export_limit_exceeded": "❌ <b>Превышен лимит!</b> Вы можете генерировать файл экспорта не более <b>2 раз в сутки</b>.",
        "export_system_busy": "⚠️ <b>Система занята.</b> В данный момент генерируется другой отчет. Пожалуйста, подождите немного, ваш запрос в очереди.",
        "export_no_purchases": "❌ У вас нет покупок за последние 3 месяца для экспорта.",
        
        "twofa_title": "🔑 <b>Двухфакторная аутентификация (2FA)</b>",
        "twofa_code_msg": "🔑 Ваш одноразовый код 2FA с сайта:\n\n<code>{code}</code>\n\n<i>Код действителен ограниченное время. Не передавайте его никому!</i>",
        "twofa_not_linked": "⚠️ Для получения кодов 2FA необходимо сначала <b>привязать ваш аккаунт</b> сайта к боту.",
        "twofa_failed": "❌ Не удалось получить код 2FA. Пожалуйста, убедитесь, что на сайте включена двухфакторная аутентификация или попробуйте позже.",
        
        "rules_text": "📜 <b>Правила сервиса Cypher</b>\n\n1. Сервис предоставляет доступ к цифровым товарам \"как есть\".\n2. Запрещено использовать сервис для незаконных действий.\n3. Все финансовые транзакции окончательны. Возвраты рассматриваются через поддержку @{support_user}.\n4. Мультиаккаунты без привязки к сайту могут быть удалены при неактивности.",
        "updates_text": "📢 <b>Обновления Cypher.Bot</b>\n\nЗдесь будут публиковаться все новости проекта, новые функции, фиксы и пополнения ассортимента товаров!\n\nСледите за обновлениями!",
        "support_text": "🤝 <b>Техническая поддержка</b>\n\nЕсли у вас возникли вопросы по оплате, привязке аккаунтов или работе сервиса, напишите нашему менеджеру:\n\n👨‍💻 <b>Контакты поддержки:</b> @{support_user}",
        
        "section_accounts": "💎 <b>Раздел Accounts (Аккаунты)</b>\n\nДанный раздел находится на стадии интеграции с сайтом. Ожидайте обновления ассортимента!",
        "section_documents": "📁 <b>Раздел Documents (Документы)</b>\n\nДанный раздел находится на стадии интеграции с сайтом. Ожидайте обновления ассортимента!",
        "section_self_reg": "⚙️ <b>Раздел Self-Reg</b>\n\nДанный раздел находится на стадии интеграции с сайтом. Ожидайте обновления ассортимента!",
        "section_fullz": "👤 <b>Раздел FULLZ</b>\n\nДанный раздел находится на стадии интеграции с сайтом. Ожидайте обновления ассортимента!",
        "section_lookup": "🔍 <b>Раздел Lookup / Пробив</b>\n\nДанный раздел находится на стадии интеграции с сайтом. Ожидайте обновления ассортимента!"
    },
    "en": {
        "welcome": (
            "🌳 Welcome to the “Cypher Market” bot\n\n"
            "⚠️ Please read the service rules before using the bot.\n\n"
            "🔥 Listings are automatically posted on our channel throughout the day, and regular updates are available here.\n\n"
            "🤓 Support - @sup_cypher\n\n"
            "🚀 We invite new suppliers to partner with us; contact support."
        ),
        "btn_accounts": "💎 Accounts",
        "btn_documents": "📁 Documents",
        "btn_self_reg": "⚙️ Self-Reg",
        "btn_fullz": "🪪 FULLZ",
        "btn_lookup": "🔍 Lookup",
        "btn_profile": "👤 Profile",
        "btn_rules": "📜 Rules",
        "btn_updates": "📢 Updates",
        "btn_support": "🤝 Support",
        "btn_toggle_lang": "Русский 🇷🇺",
        "admin_panel_welcome": (
            "👑 <b>Cypher Bot Control Panel</b>\n\n"
            "Welcome, Administrator. Please choose a management function from the menu below:"
        ),
        "admin_btn_stats": "📊 Statistics",
        "admin_btn_search": "🔍 Search User",
        "admin_btn_maintenance": "⚙️ Tech Works",
        "admin_btn_edit_texts": "📝 Edit Texts",
        "admin_btn_broadcast": "📢 Broadcast",
        "admin_btn_close": "🔙 Close",
        
        "profile_text": (
            "<b>👤 Your Cypher Profile</b>\n\n"
            "• <b>Telegram ID:</b> <code>{tg_id}</code>\n"
            "• <b>Username:</b> @{username}\n"
            "• <b>Site Login:</b> <code>{site_login}</code>\n"
            "• <b>Reg Date:</b> {reg_date}\n\n"
            "💳 <b>Balance:</b> <code>${balance:.2f}</code>\n"
            "🛍️ <b>Purchases Count:</b> <code>{purchases_count}</code>\n"
            "💰 <b>Total Spent:</b> <code>${purchases_sum:.2f}</code>"
        ),
        
        "btn_deposit": "💳 Deposit balance",
        "btn_my_purchases": "🛍️ My Purchases",
        "btn_my_deposits": "📥 My Deposits",
        "btn_link_account": "🔗 Link Account",
        "btn_account_linked_active": "✅ Account Linked ({login})",
        "btn_menu": "🔙 Menu",
        "btn_lang": "🌐 Сменить язык / Change Language",
        
        "lang_switched": "Language successfully changed to English! 🇬🇧",
        
        "link_blocked_warn": (
            "⚠️ <b>Attention! Autolink is blocked.</b>\n\n"
            "You have funds on the bot balance (<code>${balance:.2f}</code>) or purchase history.\n\n"
            "For security reasons, autolinking is disabled. "
            "Please contact the administrator @{support_user} to move your balance to the website.\n\n"
            "<i>Before doing this, be sure to press <b>My Purchases -> Export all</b> to save your local purchase history!</i>"
        ),
        
        "link_prompt": "📝 Please enter your website hash-password to link your account:",
        "link_success": "🎉 <b>Success!</b> Your Telegram account has been linked to the login <b>{login}</b> on the website.",
        "link_failed": "❌ <b>Error!</b> Invalid hash-password or the account is already linked to another user.",
        "link_cancel": "Account linking canceled.",
        
        "select_crypto": "💳 <b>Deposit Balance</b>\n\nSelect a cryptocurrency to make a payment:",
        "crypto_invoice_text": (
            "💵 <b>Deposit via {crypto}</b>\n\n"
            "To pay, send coins to the following wallet address:\n"
            "<code>{address}</code>\n\n"
            "⚠️ <b>Minimum amount:</b> <code>15 USDT</code> (or equivalent).\n"
            "{fee_warning}\n\n"
            "<i>The balance is credited automatically after network confirmations.</i>"
        ),
        "fee_usdt_warning": "💡 <b>Fee:</b> for deposits between 15 and 100 USDT, the fee is <b>5 USDT</b>. For deposits over 100 USDT, the fee is <b>0 USDT</b>.",
        "fee_other_warning": "💡 Network transaction fee is paid by the sender.",
        
        "payment_success_msg": "🎉 <b>Your balance has been successfully replenished!</b>\n\n• <b>Amount:</b> {amount} {currency}\n• <b>Equivalent:</b> ${usd_equiv:.2f}\n• <b>Method:</b> {method}\n\nThank you for your purchase!",
        
        "purchases_title": "🛍️ <b>Your recent purchases (up to 10):</b>\n\n{purchases_list}",
        "purchases_empty": "You have no purchases yet.",
        "purchases_item_format": "• {date} - <b>{product}</b>: ${amount:.2f}",
        "btn_export_all": "📥 Export all (3 months history)",
        
        "deposits_title": "📥 <b>Your recent deposits (up to 10):</b>\n\n{deposits_list}",
        "deposits_empty": "You have no deposits yet.",
        "deposits_item_format": "• {date} - {amount} {currency} (${usd:.2f}) via {method}",
        
        "export_queued": "⏳ <b>Your export request has been added to the queue!</b>\nThe worker processes files sequentially. You will receive the text file in this chat within a few minutes.",
        "export_limit_exceeded": "❌ <b>Limit exceeded!</b> You can generate the export file no more than <b>2 times a day</b>.",
        "export_system_busy": "⚠️ <b>System is busy.</b> Another report is currently being generated. Please wait, your request is in the queue.",
        "export_no_purchases": "❌ You have no purchases in the last 3 months to export.",
        
        "twofa_title": "🔑 <b>Two-Factor Authentication (2FA)</b>",
        "twofa_code_msg": "🔑 Your one-time 2FA code from the website:\n\n<code>{code}</code>\n\n<i>The code is valid for a limited time. Do not share it with anyone!</i>",
        "twofa_not_linked": "⚠️ You must first <b>link your site account</b> to the bot to obtain 2FA codes.",
        "twofa_failed": "❌ Failed to obtain 2FA code. Please ensure that two-factor authentication is enabled on the site or try again later.",
        
        "rules_text": "📜 <b>Cypher Service Rules</b>\n\n1. The service provides access to digital goods \"as is\".\n2. It is forbidden to use the service for illegal activities.\n3. All financial transactions are final. Refunds are handled via support @{support_user}.\n4. Accounts without site binding may be deleted if inactive.",
        "updates_text": "📢 <b>Cypher.Bot Updates</b>\n\nAll news, new features, fixes, and catalog additions will be posted here!\n\nStay tuned!",
        "support_text": "🤝 <b>Technical Support</b>\n\nIf you have any questions regarding payments, account linking, or bot performance, contact our manager:\n\n👨‍💻 <b>Support Contact:</b> @{support_user}",
        
        "section_accounts": "💎 <b>Accounts Section</b>\n\nThis section is currently being integrated with the site. Expect updates soon!",
        "section_documents": "📁 <b>Documents Section</b>\n\nThis section is currently being integrated with the site. Expect updates soon!",
        "section_self_reg": "⚙️ <b>Self-Reg Section</b>\n\nThis section is currently being integrated with the site. Expect updates soon!",
        "section_fullz": "👤 <b>FULLZ Section</b>\n\nThis section is currently being integrated with the site. Expect updates soon!",
        "section_lookup": "🔍 <b>Lookup Section</b>\n\nThis section is currently being integrated with the site. Expect updates soon!"
    }
}
