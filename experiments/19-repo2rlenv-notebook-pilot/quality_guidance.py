"""Keep upstream quality calls and receipts while adding controller guidance."""


class GuidedModel:
    def __init__(self, delegate, guidance):
        self.delegate = delegate
        self.guidance = guidance

    def ask(self, schema, model, system, user, key):
        return self.delegate.ask(schema, model, system + "\n\n" + self.guidance, user, key)
