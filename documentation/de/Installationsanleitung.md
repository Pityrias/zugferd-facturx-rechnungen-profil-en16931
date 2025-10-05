# Benutzerhandbuch

## Installation

### Installation von LibreOffice

Unter https://de.libreoffice.org/download/download kann LibreOffice heruntergeladen werden. Es sollte Version 25.2.5 oder neuer installiert sein. Falls Sie Hilfe bei der Installation benötigen, finden Sie eine Anleitung [hier](https://de.libreoffice.org/get-help/install-howto/)

### Installation der Erweiterung

Laden Sie die Datei `factur-x_profile_en-16931.oxt` von gitlab [hier](https://github.com/Pityrias/zugferd-facturx-rechnungen-profil-en16931) herunter. Klicken Sie dazu auf die Datei und anschließend auf den `Download raw` Button oben rechts. ![Bild Download](../images/download_oxt.jpg)

Öffnen Sie die heruntergeladene Datei mit einem Doppelklick um die Erweiterung zu installieren.
![Bild Installation](../images/install_oxt.jpg)

Die Erweiterung wird nun als installiert angezeigt. Klicken Sie auf `Schließen` und wählen Sie `Später neu starten` aus.
![Bild Installation fertig](../images/install_oxt2.jpg)

## Erstellen einer Rechnung

### Herunterladen der Vorlage

Die Erweiterung liest die Daten für den xml-Teil der E-Rechnung aus einer speziell formatierten Tabelle im zweiten Tab der Rechnungsdatei aus. Eine Rechnungsvorlage namens `factur-x_Rechnung_einfach.ods` kann [hier](https://github.com/Pityrias/zugferd-facturx-rechnungen-profil-en16931) heruntergeladen werden. Öffnen Sie die Vorlage durch einen Doppelklick.

### Einstellungen zur Makrosicherheit

Da Makros aus unbekannten Quellen ein Sicherheitsrisiko darstellen können, sind die meisten Makros in der Standardeinstellung von LibreOffice deaktiviert. Damit diese Erweiterung funktionieren kann, muss diese Einstellung angepasst werden.

Sind Makros deaktiviert, sieht die Datei nach dem Öffnen wie folgt aus:

![Bild Makros deaktiviert](../images/activate_macros3.jpg)

In diesem Fall klicken Sie in der Menüleiste auf `Extras` und dann auf `Optionen`. In folgendem Dialog wählen Sie den Unterpunkt `Sicherheit` unter `LibreOffice` aus. Dort finden Sie einen Button `Makrosicherheit`. Klicken Sie ihn an und wählen Sie dann den Punkt `Mittel` aus. Mit dieser Einstellung werden Sie bei jedem Öffnen eines Dokuments gefragt, ob Sie Makros erlauben wollen. Klicken Sie auf beide `OK` Buttons und starten Sie LibreOffice neu, damit die Änderungen wirksam werden.

![Bild Makros deaktiviert](../images/activate_macros2.jpg)

Beim Start sollten Sie jetzt folgenden Dialog sehen.

![Bild Makros deaktiviert](../images/activate_macros.jpg)

Klicken Sie auf `Makros aktivieren`.
**Hinweis: Makros können Schadsoftware enthalten. Aktivieren Sie Makros nur in Dokumenten, denen Sie vertrauen.**

### Erstellen einer ersten ZUGFERD/Factur-X Rechnung

Die Datei `factur-X_Rechnung_einfach.ods` sollte jetzt offen sein, ohne dass eine Warnung zur Makrosicherheit am oberen Rand angezeigt wird. Testen Sie die Erweiterung anhand der Vorlage. 

Führen Sie folgende Schritte aus:
1. Klicken Sie am unteren Bildschirmrand auf den Tab `Rechnung` umd die Rechnungsansicht anzuzeigen. (siehe Bild Rechnungsansicht)
2. Prüfen Sie, dass das Feld `Datum:` das aktuelle Datum enthält.
3. Scrollen Sie nach unten und prüfen Sie, dass das Datum hinter `Zu Zahlen bis zum:` in der Zukunft liegt. Wenn nicht, ändern Sie das Datum.

![Bild Rechnungsansicht](../images/ansicht_rechnung.jpg)

4. Klicken Sie am unteren Bildschirmrand auf den Tab `Daten` um die Datenansicht zu öffnen. (siehe Bild Datenansicht)
5. Klicken Sie auf den Button `Factur-X PDF Rechnung erstellen`.

![Bild Datenansicht](../images/ansicht_daten.jpg)

6. Wählen Sie einen Dateispeicherort aus, geben Sie einen Dateinamen ein und klicken Sie auf `Speichern`.

![Bild Speicherdialog](../images/rechnung_speichern.jpg)

7. Öffnen Sie das eben erstellte PDF und prüfen Sie, dass die Datei wie erwartet aussieht. Wenn Sie Adobe Acrobat zum Öffnen verwendet haben, sollte angezeigt werden, dass eine `factur-x.xml` Datei eingebettet ist.

![Bild Speicherdialog](../images/check_rechnung.jpg)

### Anpassung der Anzahl an Positionen

todo

## Anpassen der Vorlage

Das Aussehen der Rechnung kann auf vielfältige Weise angepasst werden. Dieses Kapitel erklärt, welche Möglichkeiten es gibt und was zu beachten ist.


### Wichtige Hinweise

Das finale Aussehen der Rechnung ergibt sich aus der Rechnungsansicht in Tab 1 der Vorlage. Alle kosmetischen Änderungen sollten in dieser Ansicht gemacht werden. Die Datenansicht dient als Grundlage der eingebetteten xml Datei. Dabei erwartet die Erweiterung bestimmte Daten in bestimmten Zeilen. 
**Die Zeilennummer der Einträge in der Datenansicht in Tab 2 darf NICHT verändert werden. Sonst kann keine gültige E-Rechnung generiert werden.** Die meisten Einträge der Datenansicht werden aus spezifischen Zeilen der Rechnungsansicht ausgelesen. Die Zuweisung, welche Zelle in Tab 1 den gewünschten Wert enthält, darf natürlich angepasst werden.

- Datenformat Alternative erklären

### Anpassen der Rechnungsansicht

### Anpassen der Datenansicht

### Verwendung einer Adresstabelle


