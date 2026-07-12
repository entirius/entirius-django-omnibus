
Omnibus
=======

Moduł omnibus dotyczący ceny można spłaszczyć do jednego stwierdzenia:

> Celem modułu jest wyliczyć dla konkretnego produktu cenę, po której mogliśmy produkt kupić najtaniej używając krzyżówki wszystkich, niewykluczających się, dostępnych dla większości klientów promocji.

Jako że przepisy prawne nie regulują jasno, co oznacza 'dostępna dla większości' moduł zakłada decyzje przez admina, czy reguła jest, czy nie jest 'omnibus'

Opis funkcjonalny
=================

Rozszerza reguły koszykowe o parametr:
- omnibus_rule - true/false
- parametr powinien być możliwy do zaznaczenia przez admina sklepu

Kolejność wyliczania najniższej ceny z ostatnich 30 dni:
- moduł dla SKU weryfikuje special price dla produktu - uwzględniając daty jej obowiązywania
- następnie moduł weryfikuje reguły cart stworzone na sklepie i
  - reguły muszą być oznaczone jako omnibus
  - nie można oznaczyć reguły omnibus gdy Min order amount jest różny od 0 (ograniczenie kwotowe na koszyk już sprawia że reguła na 100% nie jest omnibus)
- następnie moduł wylicza SKU które na bazie conditions mogą zostać objęte regułą
- następnie moduł stara się nałożyć wszystkie możliwe cart rule na dany produkt traktując go jakby był pojedynczo dodany do koszyka (ważne przy promocjach kwotowych)
- moduł wystawia API pozwalające odczytać po stronie frontu dodatkową cenę omnibus

Dla bardziej wytrwałych interpretacja prawna rozporządzeń UOKIK
https://docs.google.com/document/d/1HcsdEGV4bplahx7Sr2WWdBTYBBGEg77qdklH5-CyZjU/edit



Komendy
=================

Komenda fill-omnibus-product-representation-from-pim
Komenda na bazie pima uzupełnia tabele ProductRepresentation o produkty. Należy podać paramter indexu shopa pim_shop_idx, na bazie którego będą tworzone produkty w omnibus.
Przykład: manage.py fill-omnibus-product-representation-from-pim test-channel-pl


Komenda calculate_omnibus_price
przyjmuje opcjonalny parametr channel_idx. Jeżeli podamy parametr --channel_idx wartości będą przeliczane dla tego sale_channela. Jeżeli go nie podamy wartości omnibus przeliczone zostaną dla wszystkich kanałów. Komenda ta przelicza ceny według DoD w tasku i zwraca je w tabeli OmnibusPrice. Tak jak dla koszyka zostały również uwzględnione ceny specjalne pomnijeszone o reguły koszykowe. Należy pamiętać, że OmnibusPrice przeliczy wartośći discountowe tylko dla roli koszykowych, które mają włączoną flage is_omnibus w DiscountRule
Przykład: manage.py calculate_omnibus_price --channel_idx=test-channel-pl

Komenda ta oblicza ceny omnibus partiami o danej liczbie produktów w partii. Ile produktów ma być w danej partii decyduje settings BULK_SIZE_OMNIBUS (domyślnie 1000)

Tabele
=================
Tabela z danymi OmnibusPrice -Przechowuje przeliczone wartości omnibus price dla danych walut
Tabela z danymi ProductRepresentation - Przechowuje produkty
