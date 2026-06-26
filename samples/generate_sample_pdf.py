"""Generate a realistic French-style sample invoice PDF for testing."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUTPUT = "sample-invoice-fr.pdf"

def generate():
    c = canvas.Canvas(OUTPUT, pagesize=A4)
    w, h = A4

    # Header — company info
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, h - 25 * mm, "TechConsult SARL")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 32 * mm, "12 Rue de la Paix")
    c.drawString(20 * mm, h - 37 * mm, "75002 Paris, France")
    c.drawString(20 * mm, h - 42 * mm, "TVA: FR12345678901")
    c.drawString(20 * mm, h - 47 * mm, "SIRET: 123 456 789 00012")
    c.drawString(20 * mm, h - 52 * mm, "Email: contact@techconsult.fr")

    # Invoice title
    c.setFont("Helvetica-Bold", 22)
    c.drawString(120 * mm, h - 25 * mm, "FACTURE")

    # Invoice meta
    c.setFont("Helvetica", 11)
    c.drawString(120 * mm, h - 35 * mm, "Facture N°: FA-2026-042")
    c.drawString(120 * mm, h - 41 * mm, "Date: 23/06/2026")
    c.drawString(120 * mm, h - 47 * mm, "Échéance: 23/07/2026")

    # Client block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(120 * mm, h - 62 * mm, "Client:")
    c.setFont("Helvetica", 10)
    c.drawString(120 * mm, h - 68 * mm, "Expleo France SAS")
    c.drawString(120 * mm, h - 73 * mm, "48 Rue de la Victoire")
    c.drawString(120 * mm, h - 78 * mm, "75009 Paris, France")
    c.drawString(120 * mm, h - 83 * mm, "TVA: FR98765432100")

    # Separator
    y = h - 95 * mm
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.line(20 * mm, y, 190 * mm, y)

    # Table header
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Description")
    c.drawString(100 * mm, y, "Qté")
    c.drawString(115 * mm, y, "Prix Unit. HT")
    c.drawString(145 * mm, y, "TVA")
    c.drawString(165 * mm, y, "Total HT")

    c.line(20 * mm, y - 2 * mm, 190 * mm, y - 2 * mm)

    # Line items
    c.setFont("Helvetica", 10)
    items = [
        ("Conseil stratégique IT", "3", "450,00 €", "20%", "1 350,00 €"),
        ("Audit cybersécurité", "1", "1 200,00 €", "20%", "1 200,00 €"),
        ("Formation DevOps (2 jours)", "2", "800,00 €", "20%", "1 600,00 €"),
        ("Support technique mensuel", "1", "350,00 €", "20%", "350,00 €"),
    ]

    for desc, qty, unit, tva, total in items:
        y -= 8 * mm
        c.drawString(20 * mm, y, desc)
        c.drawString(103 * mm, y, qty)
        c.drawString(115 * mm, y, unit)
        c.drawString(147 * mm, y, tva)
        c.drawString(165 * mm, y, total)

    # Totals
    y -= 15 * mm
    c.line(120 * mm, y + 5 * mm, 190 * mm, y + 5 * mm)

    c.setFont("Helvetica", 11)
    c.drawString(120 * mm, y, "Total HT:")
    c.drawRightString(188 * mm, y, "4 500,00 €")

    y -= 7 * mm
    c.drawString(120 * mm, y, "TVA (20%):")
    c.drawRightString(188 * mm, y, "900,00 €")

    y -= 7 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(120 * mm, y, "Total TTC:")
    c.drawRightString(188 * mm, y, "5 400,00 €")

    # Payment info
    y -= 20 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Conditions de paiement:")
    c.setFont("Helvetica", 10)
    y -= 6 * mm
    c.drawString(20 * mm, y, "Paiement à 30 jours par virement bancaire")
    y -= 6 * mm
    c.drawString(20 * mm, y, "IBAN: FR76 3000 6000 0112 3456 7890 189")
    y -= 6 * mm
    c.drawString(20 * mm, y, "BIC: AGRIFRPP")

    # Footer
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 15 * mm, "TechConsult SARL — Capital social: 50 000 € — RCS Paris 123 456 789")

    c.save()
    print(f"Generated {OUTPUT}")

if __name__ == "__main__":
    generate()
