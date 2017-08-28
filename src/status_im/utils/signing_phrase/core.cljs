(ns status-im.utils.signing-phrase.core
  (:require [status-im.utils.signing-phrase.dictionaries.en :as en]
            [status-im.utils.signing-phrase.dictionaries.ru :as ru]
            [clojure.string :as string]))

;`signing-phrase` is a language-specific combination of three 4-lettered words
; used as an anti-phishing device.
;
; Currently only English is supported (as the default language),
; for more details see #https://github.com/status-im/status-react/issues/1679

(def dictionaries
  {:en en/dictionary
   :ru ru/dictionary})

(defn pick-words [dictionary]
  (repeatedly 3 #(rand-nth dictionary)))

(defn generate []
  (string/join " " (pick-words en/dictionary)))


