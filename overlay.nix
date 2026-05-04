final: prev: {
  webAutotender = final.python3Packages.buildPythonApplication {
    pname = "web-autotender";
    version = "1.0";

    src = final.lib.cleanSourceWith {
      src = ./.;
      filter =
        path: type:
        let
          baseName = baseNameOf (toString path);
        in
        !(builtins.elem baseName [
          "venv"
          "__pycache__"
          ".mypy_cache"
          "node_project"
          "flake.nix"
          "flake.lock"
          "overlay.nix"
        ]);
    };

    format = "other";

    dependencies = with final.python3Packages; [
      fastapi
      uvicorn
      feedparser
      sse-starlette
      asyncssh
      jinja2
    ];

    makeWrapperArgs = [ "--prefix PYTHONPATH : $out/lib/web-autotender" ];

    installPhase = ''
      mkdir -p $out/lib/web-autotender $out/bin
      cp -r pipeline_backend builtin_addons user_addons \
        $out/lib/web-autotender/
      cp main.py $out/lib/web-autotender/
      cat > $out/bin/web-autotender <<EOF
      #!/bin/sh
      cd $out/lib/web-autotender
      exec uvicorn main:app "\$@"
      EOF
      chmod +x $out/bin/web-autotender
    '';

    meta = {
      description = "Web automation workflow manager";
    };
  };
}
