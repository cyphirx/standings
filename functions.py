import datetime

# vim: set ts=4 sw=4 et :


class GMT(datetime.tzinfo):
    def utcoffset(self, dt):
      return datetime.timedelta(hours=0)

    def dst(self, dt):
        return datetime.timedelta(0)

def standings_bgcolor(value):
    if value < -5:
        bgcolor = "terrible"
    elif -5 <= value < 0:
        bgcolor = "bad"
    elif 0 < value <= 5:
        bgcolor = "good"
    elif value > 5:
        bgcolor = "excellent"
    else:
        bgcolor = "neutral"
    return bgcolor