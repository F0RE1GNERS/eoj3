from django import forms


class CommaSeparatedMultipleChoiceField(forms.MultipleChoiceField):

    def _split_comma(self, value):
        return list(filter(lambda u: u, map(lambda t: t.strip(), value.split(','))))

    def to_python(self, value):
        if ',' in value:
            return self._split_comma(value)
        if isinstance(value, (tuple, list)):
            return self._split_comma(value[0])
        return super(CommaSeparatedMultipleChoiceField, self).to_python(value)
