"""
order_store.py
ProfiDO (KSB_ProfilKesim) — Akıllı Üretim sipariş/çizim kalıcılığı.

Bir "sipariş", bir veya daha fazla "çizim" (çerçeve) içeren, isim/müşteri
bilgisiyle etiketlenmiş bir kayıttır. Her sipariş, ~/.ksb_profil/orders/
altında tek bir JSON dosyası olarak saklanır (dosya adı: order_id.json).

Dosya konumu: ~/.ksb_profil/orders/<order_id>.json

Bir sipariş sözlüğünün (order dict) şekli (bkz. ui/dialog_akilli_uretim.py
AkilliUretimDialog._gather_order_dict / load_order_data):
    {
        'order_id':      str,          # uuid tabanlı benzersiz kimlik
        'order_no':      str,          # kullanıcının girdiği sipariş no (örn. 'S12')
        'customer_name': str,
        'customer_code': str,
        'bar_len_mm':    int,
        'bar_start':     int,
        'prog_start':    int,
        'frames':        [ {...çizim kaydı...}, ... ],
        'created_at':    str (ISO 8601, bu modül tarafından eklenir/korunur),
        'updated_at':    str (ISO 8601, bu modül tarafından her kayıtta güncellenir),
    }

Bu modül sadece düz JSON okuma/yazma yapar; iş mantığı (örn. cell_assigns
tuple<->list dönüşümü) çağıran taraftadır (AkilliUretimDialog).
"""

import json
import os
import uuid
import datetime
import paths

_ORDERS_DIR = os.path.join(paths.app_data_dir(), 'orders')


def orders_dir() -> str:
    """Siparişlerin saklandığı klasörü döndürür, yoksa oluşturur."""
    os.makedirs(_ORDERS_DIR, exist_ok=True)
    return _ORDERS_DIR


def _order_path(order_id: str) -> str:
    return os.path.join(orders_dir(), f'{order_id}.json')


def list_orders() -> list:
    """Tüm siparişlerin özet bilgilerini (tam frame verisi olmadan) döndürür,
    son güncellemeye göre en yeniden en eskiye sıralı.

    Her öğe: {'order_id', 'order_no', 'customer_name', 'customer_code',
              'frame_count', 'piece_count', 'updated_at', 'created_at'}
    """
    d = orders_dir()
    out = []
    for fname in os.listdir(d):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(d, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        frames = data.get('frames', []) or []
        piece_count = sum(len(fr.get('pieces', []) or []) for fr in frames)
        out.append({
            'order_id':      data.get('order_id') or os.path.splitext(fname)[0],
            'order_no':      data.get('order_no', ''),
            'customer_name': data.get('customer_name', ''),
            'customer_code': data.get('customer_code', ''),
            'frame_count':   len(frames),
            'piece_count':   piece_count,
            'created_at':    data.get('created_at', ''),
            'updated_at':    data.get('updated_at', ''),
        })
    out.sort(key=lambda o: o.get('updated_at', ''), reverse=True)
    return out


def load_order(order_id: str) -> dict:
    """Belirtilen siparişin tam verisini yükler. Bulunamazsa None döner."""
    path = _order_path(order_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_order(order: dict) -> str:
    """Siparişi diske kaydeder (yeni ise oluşturur, mevcutsa günceller).
    order_id yoksa yeni bir tane üretir. Atomik yazma (tmp + os.replace)
    kullanılarak yarım yazılmış/bozuk dosya riski önlenir.

    Döndürür: order_id (str)
    """
    order = dict(order)  # kopya — çağıranın sözlüğünü mutasyona uğratma
    order_id = order.get('order_id')
    now = datetime.datetime.now().isoformat(timespec='seconds')

    if not order_id:
        order_id = uuid.uuid4().hex[:12]
        order['order_id'] = order_id
        order['created_at'] = now
    else:
        # created_at korunsun — mevcut dosyadan al (varsa)
        existing = load_order(order_id)
        order['created_at'] = (existing or {}).get('created_at', now)

    order['updated_at'] = now

    path = _order_path(order_id)
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(order, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    return order_id


def delete_order(order_id: str) -> bool:
    """Siparişi diskten siler. Başarılıysa True, dosya yoksa False döner."""
    path = _order_path(order_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
