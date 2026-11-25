import Lake
open Lake DSL

package «DominoesCommonFigure» where
  srcDir := "."

@[default_target]
lean_lib «DominoesCommonFigure» where
  roots := #[`DominoesCommonFigure]
