GOOD_THRESHOLD = 75
AVERAGE_THRESHOLD = 50

RECOMMENDATIONS = {
    "Poor": "Recommend remedial sessions and revisiting fundamentals",
    "Average": "Recommend targeted practice on weak topics",
    "Good": "Recommend enrichment/advanced material",
}


def classify(marks_obtained, max_marks):
    if max_marks <= 0:
        return "Poor"
    percentage = (marks_obtained / max_marks) * 100
    if percentage >= GOOD_THRESHOLD:
        return "Good"
    if percentage >= AVERAGE_THRESHOLD:
        return "Average"
    return "Poor"


def recommendation_for(classification):
    return RECOMMENDATIONS.get(classification, RECOMMENDATIONS["Average"])
