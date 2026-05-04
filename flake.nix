{
  inputs = {
    nixpkgs = {
      url = "github:NixOS/nixpkgs?ref=nixos-unstable";
    };
  };
  outputs =
    { self, nixpkgs, ... }@flakeInputs:
    let
      forAllSystems = nixpkgs.lib.genAttrs nixpkgs.lib.systems.flakeExposed;
    in
    {
      inherit nixpkgs;
      overlays = {
        default = import ./overlay.nix;
      };
      legacyPackages = forAllSystems (
        system: nixpkgs.legacyPackages.${system}.appendOverlays (builtins.attrValues self.overlays)
      );
      formatter = forAllSystems (system: self.legacyPackages.${system}.nixfmt-tree);
      packages = forAllSystems (system: {
        inherit (self.legacyPackages.${system}) webAutotender;
        default = self.legacyPackages.${system}.webAutotender;
      });
      apps = forAllSystems (system: {
        webAutotender = {
          type = "app";
          program = "${self.legacyPackages.${system}.webAutotender}/bin/web-autotender";
        };
        default = self.apps.${system}.webAutotender;
      });
      devShells = forAllSystems (
        system:
        (
          let
            pkgs = self.legacyPackages.${system};
            pythonPackages = pkgs.python3Packages;
          in
          {
            default = pkgs.mkShell {
              name = "web-autotender dev shell";
              buildInputs =
                (with pkgs; [
                ])
                ++ (with pythonPackages; [
                  python
                  ruff
                  fastapi
                  uvicorn
                  feedparser
                  sse-starlette
                  asyncssh
                  jinja2
                  python-multipart
                  regex
                ]);
              shellHook = ''
                export PS1='\n(dev) \[\033[1;32m\][\[\e]0;\u@\h: \w\a\]\u@\h:\w]\$\[\033[0m\] '
                export PYTHONPATH=$PYTHONPATH
              '';
            };
          }
        )
      );
    };
}
