from debug_toolbar.panels.templates import TemplatesPanel as BaseTemplatesPanel

class TemplatesPanel(BaseTemplatesPanel):
    def generate_stats(self, *args):
        template = self.templates[0]['template']
        if not hasattr(template, 'engine') and hasattr(template, 'backend'):
            template.engine = template.backend
        return super().generate_stats(*args)