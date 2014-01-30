import datetime

# vim: set ts=4 sw=4 et :


class GMT(datetime.tzinfo):
    def utcoffset(self, dt):
      return datetime.timedelta(hours=0)

    def dst(self, dt):
        return datetime.timedelta(0)