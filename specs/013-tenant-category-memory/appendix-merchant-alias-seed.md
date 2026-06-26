# Appendix: Merchant Alias Seed (YAML)

**Feature**: 013-tenant-category-memory  
**Deliverable**: `data/merchant_aliases_ja.yaml` (repo-seeded; no runtime UI)

## Format

```yaml
# merchant_key: list of variant strings (case/spacing insensitive after normalization)
seven_eleven:
  - セブン-イレブン
  - セブンイレブン
  - 7-ELEVEN
  - 7-11
  - ｾﾌﾞﾝｲﾚﾌﾞﾝ
familymart:
  - ファミリーマート
  - ファミマ
  - FamilyMart
  - FAMILYMART
```

Rules:
- Keys are lowercase ASCII snake_case (`merchant_key`).
- Variants include Japanese, katakana, half-width katakana, romaji, and common abbreviations.
- Branch suffixes (`○○店`, `駅前`) are stripped by normalizer, not listed as aliases.
- Generic terms (`食費`, `買い物`) belong in generic denylist, not aliases.

## Minimum seed coverage (v1)

Implementers MUST seed at least the merchants below. Group by sector for maintenance.

### Convenience stores (コンビニ)

| merchant_key | Variants to include |
|--------------|---------------------|
| `seven_eleven` | セブン-イレブン, セブンイレブン, 7-ELEVEN, 7-11, ｾﾌﾞﾝｲﾚﾌﾞﾝ |
| `familymart` | ファミリーマート, ファミマ, FamilyMart |
| `lawson` | ローソン, LAWSON, ナチュラルローソン, ローソン100 |
| `ministop` | ミニストップ, MINISTOP |
| `daily_yamazaki` | デイリーヤマザキ, ヤマザキデイリー |
| `newdays` | ニューデイズ, NewDays |
| `seicomart` | セイコーマート, Seicomart |
| `poplar` | ポプラ, Poplar |
| `three_f` | スリーエフ, 3F |
| `coco_store` | ココストア, Coco Store |

### Supermarkets & discount grocery (スーパー・食品ディスカウント)

| merchant_key | Variants |
|--------------|----------|
| `aeon` | イオン, AEON, まいばすけっと, マイバスケット, My Basket |
| `life` | ライフ, LIFE, ライフコーポレーション |
| `summit` | サミット, Summit |
| `maruetsu` | マルエツ, マルエツプチ |
| `kasumi` | カスミ, フードスクエアカスミ |
| `yaoko` | ヤオコー, Yaoko |
| `belc` | ベルク, Belc |
| `valor` | バロー, Valor, ホームセンターバロー |
| `ion` | いなげや (Inageya) — separate key `inageya` |
| `inageya` | いなげや, Inageya |
| `ok` | オーケー, OK, オーケーストア |
| `gyomu_super` | 業務スーパー, 業スー |
| `trial` | トライアル, Trial |
| `don_quijote` | ドン・キホーテ, ドンキ, ドンキホーテ, Don Quijote |
| `seiyu` | 西友, SEIYU |
| `lopia` | ロピア, Lopia |
| `york` | ヨーク, York, ヨークベニマル |
| `maxvalu` | マックスバリュ, MaxValu |
| `halods` | ハローズ, Harrows |

### Drugstores (ドラッグストア)

| merchant_key | Variants |
|--------------|----------|
| `matsumoto_kiyoshi` | マツモトキヨシ, マツキヨ, Matsumoto Kiyoshi |
| `welcia` | ウエルシア, Welcia, ハックドラッグ, ダックス |
| `tsuruha` | ツルハ, Tsuruha, ツルハドラッグ |
| `sugi` | スギ薬局, スギドラッグ, Sugi |
| `cosmos` | コスモス, Cosmos |
| `sun_drug` | サンドラッグ, Sun Drug |
| `create_sd` | クリエイトSD, クリエイトエスディー |
| `cocokara_fine` | ココカラファイン, Cocokara Fine |

### Dining & cafe (外食・カフェ)

| merchant_key | Variants |
|--------------|----------|
| `starbucks` | スターバックス, Starbucks, スタバ |
| `doutor` | ドトール, Doutor |
| `tullys` | タリーズ, Tully's |
| `komeda` | コメダ珈琲, コメダ, Komeda |
| `saizeriya` | サイゼリヤ, Saizeriya |
| `matsuya` | 松屋, Matsuya |
| `yoshinoya` | 吉野家, Yoshinoya |
| `sukiya` | すき家, Sukiya |
| `nakau` | なか卯, Nakau |
| `coco_ichi` | ココイチ, ココイチバンヤ, CoCo壱 |
| `mos_burger` | モスバーガー, MOS BURGER |
| `mcdonalds` | マクドナルド, マック, McDonald's |
| `kfc` | ケンタッキー, KFC, ケンタ |
| `skylark` | すかいらーく, ガスト, バーミヤン, しゃぶ葉, ジョナサン |
| `royal_host` | ロイヤルホスト, Royal Host |
| `denny`s` | デニーズ, Denny's |
| `pronto` | プロント, Pronto |
| `excelsior` | エクセルシオール, Excelsior |

### Fast food & bakery

| merchant_key | Variants |
|--------------|----------|
| `mister_donut` | ミスタードーナツ, ミスド |
| `kura_sushi` | くら寿司, Kura Sushi |
| `hamazushi` | はま寿司, Hamazushi |
| `sushiro` | スシロー, Sushiro |
| `yamazaki_bakery` | ヤマザキパン, デイリーヤマザキ (if not convenience) |

### Transport & mobility

| merchant_key | Variants |
|--------------|----------|
| `japan_railways` | JR, JR東日本, JR西日本, JR東海, JR九州, JR四国 |
| `tokyo_metro` | 東京メトロ, メトロ |
| `toei_subway` | 都営地下鉄, 都営 |
| `uber` | Uber, ウーバー, Uber Eats, ウーバーイーツ |
| `didi` | DiDi, ディディ |
| `go_taxi` | GO, GOタクシー |
| `japan_taxi` | 日本交通, 国際自動車 |
| `suica` | Suica, スイカ |
| `pasmo` | PASMO, パスモ |
| `icoca` | ICOCA, イコカ |
| `nimoca` | nimoca |
| `pitapa` | PiTaPa |

### Delivery & EC

| merchant_key | Variants |
|--------------|----------|
| `amazon` | Amazon, アマゾン, Amazon.co.jp |
| `rakuten` | 楽天, Rakuten, 楽天市場 |
| `mercari` | メルカリ, Mercari |
| `yahoo_shopping` | Yahoo!ショッピング, PayPayモール |
| `demae_can` | 出前館 |
| `uber_eats` | (alias under `uber` or separate if split) |

### Home center & electronics

| merchant_key | Variants |
|--------------|----------|
| `nitori` | ニトリ, Nitori |
| `ikea` | IKEA, イケア |
| `muji` | 無印良品, MUJI |
| `daiso` | ダイソー, Daiso, セリア, Seria, キャンドゥ, Can Do |
| `yamada_denki` | ヤマダデンキ, ヤマダ電機 |
| `bic_camera` | ビックカメラ, BicCamera |
| `yodobashi` | ヨドバシカメラ, Yodobashi |
| `kojima` | コジマ, Kojima |
| `edion` | エディオン, Edion |
| `hard_off` | ハードオフ, オフハウス, Book Off, ブックオフ |

### Telecom & utilities (common on receipts)

| merchant_key | Variants |
|--------------|----------|
| `ntt_docomo` | NTTドコモ, docomo |
| `au` | au, KDDI |
| `softbank` | ソフトバンク, SoftBank |
| `rakuten_mobile` | 楽天モバイル |
| `tokyo_gas` | 東京ガス |
| `tepco` | 東京電力, TEPCO |

## Target size

- **Minimum**: 60 `merchant_key` entries (above list)
- **Stretch**: 100+ entries including regional chains (セイミヤ, フジ, 平和堂, イズミ, etc.)

## Maintenance

- New aliases via PR to `data/merchant_aliases_ja.yaml` only.
- No user-facing alias editor in v1.
