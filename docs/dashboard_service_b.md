# DashboardService — اتصال B و C برای سعید

این سرویس جدید متعلق به کار یکپارچه‌سازی دانیال است. کد وب سعید و کد، فرمول امتیاز، تست‌ها و مستندات حنانه تغییر نکرده‌اند. این فایل راهنمای اتصال پیشنهادی است؛ تغییر مسیر Flask و قالب باید در بخش سعید انجام شود.

## فایل‌ها و مسئولیت‌ها

- `smart_energy/analytics/dashboard_service.py`: کلاس جدید `DashboardService`؛ فقط خواندن داده و هماهنگی سرویس‌ها.
- `PeriodAnalyticsService`: محاسبات انرژی، پوشش، مرجع و ساعات غیرکاری؛ بدون تغییر.
- `ScoreCalculator` حنانه: محاسبه امتیاز و جریمه‌ها؛ بدون تغییر و به صورت dependency به سرویس تزریق می‌شود.
- `demo_dashboard_b.py`: نمونهٔ کامل خروجی با دادهٔ شبیه‌سازی‌شده یا MySQL فقط‌خواندنی.
- `tests/test_dashboard_service_b.py`: تست‌های اتصال، قرارداد خروجی و حالات ناقص/خطا.

امتیاز در Python محاسبه می‌شود و به اتصال OpenAI نیاز ندارد. این سرویس AI Coach را فراخوانی یا Blueprint آن را ثبت نمی‌کند؛ آن اتصال جداگانه باقی می‌ماند.

## نمونهٔ استفاده در مسیر وب

کد زیر را سعید در بخش خودش با تنظیمات برنامه هماهنگ کند. تنظیمات نمونه‌اند؛ برای ساختمان واقعی باید با مالک داده تأیید شوند.

```python
from decimal import Decimal
from smart_energy.analytics.dashboard_service import DashboardService
from smart_energy.analytics.operating_schedule import OperatingSchedule
from smart_energy.analytics.period_analytics import to_json_ready
from smart_energy.analytics.time_window import TimeWindow
from smart_energy.coach.score_calculator import ScoreCalculator

schedule = OperatingSchedule(
    "Europe/Berlin",
    {day: [("09:00", "17:00")] for day in range(5)},
)
service = DashboardService.from_database(
    db,  # همان نمونهٔ Database در بخش B
    tariff=Decimal("0.30"),
    carbon_factor=Decimal("0.40"),
    allowance_share=Decimal("0.10"),
    schedule=schedule,
    score_calculator_factory=ScoreCalculator,
)
window = TimeWindow(start_time, end_time)  # datetime های دارای timezone
summary = service.build_summary(building_id, meter_id, window)
# API:
# return jsonify(to_json_ready(summary))
# HTML:
# return render_template("dashboard.html", summary=summary, ...)
```

سرویس از همان Repositoryهای B استفاده می‌کند؛ برای این خروجی، وب نیازی به خواندن مجدد قرائت‌ها یا فراخوانی مستقیم `compare` و `calculate` ندارد. ساخت `Database` از تنظیمات امن محیط انجام می‌شود؛ رمز را در کد قرار ندهید.

**بازهٔ مرجع پیش‌فرض:** بازهٔ بلافاصله قبل از بازهٔ انتخاب‌شده، با طول برابر برحسب زمان سپری‌شدهٔ UTC. این تعریف لزوماً «روز کاری مشابه» نیست. برای مرجع مشخص:

```python
summary = service.build_summary(building_id, meter_id, window, reference_window)
```

مرجع صریح باید هم‌مدت و قبل از دورهٔ فعلی باشد. برای نمونهٔ E=5/R=7/O=2، مرجع روز قبل ساعت ۸ تا ۱۰ برلین را صریحاً بدهید؛ مرجع خودکارِ یک دورهٔ ۸ تا ۱۰، همان روز ساعت ۶ تا ۸ است و ممکن است داده نداشته باشد.

## قرارداد خروجی واحد

خروجی به صورت دیکشنری تخت، شامل تمام کلیدهای خلاصهٔ دورهٔ فعلی B و موارد زیر است:

| کاربرد در وب | کلید |
|---|---|
| نام ساختمان / کنتور | `building_name` / `meter_name` |
| انرژی، هزینه، کربن | `energy_kwh` / `estimated_cost_eur` / `estimated_co2_kg` |
| وضعیت و پوشش دادهٔ فعلی | `status` / `coverage_fraction` |
| نمودار و شکاف‌های اندازه‌گیری | `series` / `gaps` |
| آخرین انرژی داخل بازهٔ انتخاب‌شده | `latest_interval_kwh` |
| زمان و علامت تخمینی آخرین بازه | `latest_interval`، شامل `start`، `end`، `energy_estimated` |
| خلاصهٔ مرجع و سیاست انتخاب آن | `reference` / `reference_policy` |
| وضعیت مقایسه | `comparison.status` |
| تغییر مصرف نسبت به مرجع | `comparison.energy_change_percent` |
| صرفه‌جویی نسبی (با علامت مخالف تغییر) | `comparison.energy_saved_percent` |
| صرفه‌جویی انرژی، هزینه و کربن | `comparison.energy_saved_kwh` / `cost_saved_eur` / `co2_saved_kg` |
| امتیاز و وضعیت آن | `score` / `score_status` |
| جریمه‌ها | `penalties.growth_penalty` / `penalties.off_hours_penalty` |
| ورودی امتیاز و کیفیت آن | `score_inputs` / `score_inputs_status` / `score_inputs_estimated` |
| سهم مجاز مشترک | `score_allowance_share` |

نمونهٔ خلاصه‌شدهٔ سناریوی شبیه‌سازی‌شده پس از `to_json_ready`:

```json
{
  "energy_kwh": "5",
  "estimated_cost_eur": "1.50",
  "estimated_co2_kg": "2.00",
  "off_hours_energy_kwh": "2",
  "latest_interval_kwh": "3",
  "score": "74.0",
  "score_status": "ready",
  "penalties": {"growth_penalty": "0.0", "off_hours_penalty": "26.0"}
}
```

نسخهٔ فعلی شاخهٔ حنانه score و جریمه‌ها را `float` می‌دهد؛ نسخهٔ موجود در شاخهٔ B آن‌ها را `Decimal` می‌دهد. هر دو با این سرویس سازگارند؛ در JSON مقدارهای Decimal رشته و float عدد هستند. فرانت در صورت نیاز به قالب‌بندی عدد، مقدار غیر-null را تبدیل کند. سایر مقدارهای مالی/انرژی دقیقاً با `to_json_ready` رشته می‌شوند.

## نکات ضروری برای قالب و API

```jinja2
{% if summary.score_status == 'ready' and summary.score is not none %}
  {{ '%.1f'|format(summary.score|float) }} / 100
{% else %}
  Not available
{% endif %}
```

- **امتیاز صفر معتبر است.** از شرط `if summary.score` استفاده نشود.
- برای نبود داده، انرژی/هزینه/کربن/آخرین بازه `None` باقی می‌مانند. آن‌ها را با صفر جایگزین نکنید.
- پوشش ناقص `partial` است؛ مقدارها فقط مربوط به قرائت‌های موجودند و به کل دوره تعمیم داده نمی‌شوند. امتیاز و مقایسه در نبود پوشش کامل unavailable هستند.
- در نبود تقویم، O و امتیاز unavailable می‌مانند؛ تقویم فرضی به صورت خودکار اضافه نمی‌شود.
- اگر `score_inputs_estimated` درست است، امتیاز بر ورودی تخمینی استوار است و باید مشخص شود. تخصیص قرائت‌های عبوری از مرز زمانی بر فرض توان متوسط ثابت است.
- Energy change برای E=5 و R=7 حدود **منفی ۲۸٫۶٪** است؛ savings حدود **مثبت ۲۸٫۶٪** است.
- `latest_interval` مربوط به آخرین بخش قرائت در بازهٔ انتخاب‌شده است، نه آخرین دادهٔ کل دیتابیس یا توان لحظه‌ای. زمان آن را هم نمایش دهید.
- درخواست HTML و API باید از همین سرویس و تنظیم مشترک استفاده کنند تا نتایج یکسان بماند.
- خطاها پنهان نمی‌شوند: `building_not_found` و `meter_not_found` را در وب به وضعیت مناسب، مثلاً 404، نگاشت کنید. خطای دیتابیس یا محاسبه‌گر نباید به پاسخ موفقِ صفر تبدیل شود. از handlerهای موجود در مرز وب استفاده کنید.

## اجرا و تست

```bash
python demo_dashboard_b.py
python -m pytest tests/test_dashboard_service_b.py -v
```

دموی پیش‌فرض به دیتابیس یا OpenAI وصل نمی‌شود، ولی محاسبات واقعی B و کلاس واقعی C را اجرا می‌کند. نتیجهٔ نمونه: انرژی ۵، مرجع ۷، خارج ساعات کاری ۲، هزینه ۱٫۵۰ یورو، کربن ۲ کیلوگرم، Score برابر ۷۴.

برای خواندن داده‌های تاریخی موجود در MySQL، پس از تنظیم متغیرهای محیط:

```bash
python demo_dashboard_b.py --mysql
```

این دستور داده‌ای اضافه یا ویرایش نمی‌کند. دادهٔ شبیه‌سازی‌شده را به عنوان دادهٔ زنده نشان ندهید. وجود دادهٔ نمونهٔ تاریخی به معنی پوشش بازهٔ «۲۴ ساعت اخیر» نیست.

Docker فعلی B همچنان runner محاسبات مستقل B است و C را بسته‌بندی نمی‌کند؛ اجرای دموی هماهنگ‌کننده به کد C هم نیاز دارد. این تغییر به معنی تکمیل Docker وب/AI یا تکمیل اتصال نهایی داشبورد نیست.

## نتیجهٔ بررسی این تغییر — ۱۱ نوامبر ۲۰۲۶

- کل تست‌های موجود در شاخهٔ B پس از تغییر: **۷۷ passed**.
- تست‌های جدید هماهنگ‌کننده: **۱۵ passed**.
- همان ۱۵ تست با کلاس `ScoreCalculator` دریافت‌شده از شاخهٔ `capstone-hananeh-c` در commit `92be6bf` نیز پاس شدند؛ کلاس فقط برای اجرای بررسی در حافظه بارگذاری شد و فایل C تغییر نکرد.
- دموی حافظه‌ای با محاسبات واقعی B/C اجرا شد و score=74 را در خروجی واحد برگرداند.
- در این مرحله اتصال MySQL واقعی، اجرای Docker جدید، ثبت Blueprint مربی، درخواست واقعی OpenAI و نمایش مسیر وب جدید انجام نشده‌اند. `--mysql` فقط نمونهٔ آمادهٔ اجرا است؛ موفقیت آن در این تغییر ادعا نمی‌شود.
- در این تغییر هیچ فایل موجود A/C و هیچ بخش قبلی README ویرایش نشد؛ فقط بخش جدید B به انتهای README اضافه شد.
