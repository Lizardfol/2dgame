package main

import (
	"fmt"
	"image/color"
	"math"
	"math/rand"
	"strconv"
	"time"

	"github.com/hajimehoshi/ebiten/v2"
	"github.com/hajimehoshi/ebiten/v2/text"
	"github.com/hajimehoshi/ebiten/v2/vector"
	"golang.org/x/image/font/basicfont"
)

const (
	WIDTH          = 1280
	HEIGHT         = 720
	TILE_SIZE      = 32
	ROWS           = 64
	COLS           = 128
	GRAVITY        = 0.5
	JUMP_POWER     = -10
	MAX_FALL_SPEED = 12
)

type BlockType struct {
	Color    color.RGBA
	Hardness int
	Value    int // Numeric value to display on block
}

var BLOCK_TYPES = map[string]BlockType{
	"dirt":        {Color: color.RGBA{139, 69, 19, 255}, Hardness: 1, Value: 1},
	"stone":       {Color: color.RGBA{128, 128, 128, 255}, Hardness: 2, Value: 2},
	"iron":        {Color: color.RGBA{210, 210, 210, 255}, Hardness: 3, Value: 3},
	"gold":        {Color: color.RGBA{255, 215, 0, 255}, Hardness: 3, Value: 4},
	"diamond":     {Color: color.RGBA{185, 242, 255, 255}, Hardness: 4, Value: 5},
	"unbreakable": {Color: color.RGBA{0, 0, 0, 255}, Hardness: math.MaxInt32, Value: 9},
	"wood":        {Color: color.RGBA{139, 69, 19, 255}, Hardness: 1, Value: 6},
	"leaves":      {Color: color.RGBA{34, 139, 34, 255}, Hardness: 1, Value: 7},
}

type Block struct {
	Type  string
	Value int
}

type Player struct {
	X, Y          float64
	VelX, VelY    float64
	Width, Height float64
	Health        float64
	MaxHealth     float64
	Inventory     map[string]int
	OnGround      bool
	MiningProgress float64
	MiningTarget  *[2]int
}

type Game struct {
	World     [][]*Block
	Player    *Player
	CameraX   float64
	CameraY   float64
	TimeOfDay float64
}

func NewGame() *Game {
	g := &Game{
		TimeOfDay: 0,
	}
	g.generateWorld()
	g.createPlayer()
	return g
}

func (g *Game) generateWorld() {
	g.World = make([][]*Block, ROWS)
	for i := range g.World {
		g.World[i] = make([]*Block, COLS)
	}

	// Generate base heights
	baseHeights := make([]int, COLS)
	for i := range baseHeights {
		baseHeights[i] = ROWS / 2
		if i > 0 {
			diff := rand.Intn(5) - 2
			baseHeights[i] = baseHeights[i-1] + diff
			if baseHeights[i] < ROWS/4 {
				baseHeights[i] = ROWS / 4
			} else if baseHeights[i] > ROWS*3/4 {
				baseHeights[i] = ROWS * 3 / 4
			}
		}
	}

	// Generate terrain
	for x := 0; x < COLS; x++ {
		height := baseHeights[x]
		treeChance := rand.Float64()

		for y := 0; y < ROWS; y++ {
			if y >= height {
				var blockType string
				if y == height {
					blockType = "dirt"
				} else if y < height+5 {
					blockType = "dirt"
				} else {
					r := rand.Float64()
					if r < 0.01 && y < ROWS-10 {
						blockType = "diamond"
					} else if r < 0.03 && y < ROWS-5 {
						blockType = "gold"
					} else if r < 0.08 && y < ROWS-5 {
						blockType = "iron"
					} else {
						blockType = "stone"
					}
				}

				// Generate trees
				if y == height && treeChance < 0.2 {
					treeHeight := rand.Intn(4) + 3
					for ty := 0; ty < treeHeight; ty++ {
						if y-ty >= 0 {
							g.World[y-ty][x] = &Block{
								Type:  "wood",
								Value: BLOCK_TYPES["wood"].Value,
							}
						}
					}

					// Add leaves
					leafSizes := []int{1, 3, 5, 3, 1}
					for ly, width := range leafSizes {
						start := max(0, x-width/2)
						end := min(COLS, x+width/2+1)
						for lx := start; lx < end; lx++ {
							if y-treeHeight-ly >= 0 {
								g.World[y-treeHeight-ly][lx] = &Block{
									Type:  "leaves",
									Value: BLOCK_TYPES["leaves"].Value,
								}
							}
						}
					}
				}

				if g.World[y][x] == nil {
					g.World[y][x] = &Block{
						Type:  blockType,
						Value: BLOCK_TYPES[blockType].Value,
					}
				}
			}
		}
	}

	// Add unbreakable bottom layer
	for x := 0; x < COLS; x++ {
		g.World[ROWS-1][x] = &Block{
			Type:  "unbreakable",
			Value: BLOCK_TYPES["unbreakable"].Value,
		}
	}
}

func (g *Game) createPlayer() {
	spawnX, spawnY := COLS/2, 0
	for y := 0; y < ROWS; y++ {
		if g.World[y][spawnX] != nil {
			spawnY = y - 2
			break
		}
	}

	g.Player = &Player{
		X:         float64(spawnX * TILE_SIZE),
		Y:         float64(spawnY * TILE_SIZE),
		Width:     TILE_SIZE,
		Height:    TILE_SIZE * 2,
		Health:    100,
		MaxHealth: 100,
		Inventory: make(map[string]int),
	}
}

func (g *Game) Update() error {
	g.handleInput()
	g.updatePlayer()
	g.updateCamera()
	return nil
}

func (g *Game) handleInput() {
	// Movement
	if ebiten.IsKeyPressed(ebiten.KeyLeft) {
		g.Player.VelX = -6
	} else if ebiten.IsKeyPressed(ebiten.KeyRight) {
		g.Player.VelX = 6
	} else {
		g.Player.VelX *= 0.8 // Friction
	}

	// Jump
	if ebiten.IsKeyPressed(ebiten.KeySpace) && g.Player.OnGround {
		g.Player.VelY = JUMP_POWER
	}

	// Mining
	if ebiten.IsMouseButtonPressed(ebiten.MouseButtonLeft) {
		x, y := ebiten.CursorPosition()
		gridX := int((float64(x) + g.CameraX) / TILE_SIZE)
		gridY := int((float64(y) + g.CameraY) / TILE_SIZE)

		if gridX >= 0 && gridX < COLS && gridY >= 0 && gridY < ROWS {
			g.handleMining(gridX, gridY)
		}
	}
}

func (g *Game) handleMining(gridX, gridY int) {
	if g.World[gridY][gridX] == nil {
		return
	}

	block := g.World[gridY][gridX]
	if block.Type == "unbreakable" {
		return
	}

	playerCenterX := g.Player.X + g.Player.Width/2
	playerCenterY := g.Player.Y + g.Player.Height/2
	blockCenterX := float64(gridX*TILE_SIZE) + TILE_SIZE/2
	blockCenterY := float64(gridY*TILE_SIZE) + TILE_SIZE/2

	distance := math.Sqrt(math.Pow(playerCenterX-blockCenterX, 2) + math.Pow(playerCenterY-blockCenterY, 2))
	if distance < TILE_SIZE*5 {
		g.Player.MiningProgress += 1
		if g.Player.MiningProgress >= float64(BLOCK_TYPES[block.Type].Hardness*20) {
			g.Player.Inventory[block.Type]++
			g.World[gridY][gridX] = nil
			g.Player.MiningProgress = 0
		}
	}
}

func (g *Game) updatePlayer() {
	// Apply gravity
	g.Player.VelY = min(g.Player.VelY+GRAVITY, MAX_FALL_SPEED)

	// Update position with collision
	newX := g.Player.X + g.Player.VelX
	newY := g.Player.Y + g.Player.VelY

	// Horizontal movement
	if !g.checkCollision(newX, g.Player.Y) {
		g.Player.X = newX
	}

	// Vertical movement
	g.Player.OnGround = false
	if !g.checkCollision(g.Player.X, newY) {
		g.Player.Y = newY
	} else {
		if g.Player.VelY > 0 {
			g.Player.OnGround = true
		}
		g.Player.VelY = 0
	}
}

func (g *Game) checkCollision(x, y float64) bool {
	points := [][2]float64{
		{x, y},
		{x + g.Player.Width - 1, y},
		{x, y + g.Player.Height - 1},
		{x + g.Player.Width - 1, y + g.Player.Height - 1},
	}

	for _, p := range points {
		gridX := int(p[0] / TILE_SIZE)
		gridY := int(p[1] / TILE_SIZE)
		if gridX >= 0 && gridX < COLS && gridY >= 0 && gridY < ROWS {
			if g.World[gridY][gridX] != nil {
				return true
			}
		}
	}
	return false
}

func (g *Game) updateCamera() {
	targetX := g.Player.X - WIDTH/2 + g.Player.Width/2
	targetY := g.Player.Y - HEIGHT/2 + g.Player.Height/2

	g.CameraX += (targetX - g.CameraX) * 0.1
	g.CameraY += (targetY - g.CameraY) * 0.1

	g.CameraX = max(0, min(float64(COLS*TILE_SIZE-WIDTH), g.CameraX))
	g.CameraY = max(0, min(float64(ROWS*TILE_SIZE-HEIGHT), g.CameraY))
}

func (g *Game) Draw(screen *ebiten.Image) {
	// Clear screen with sky color
	screen.Fill(color.RGBA{135, 206, 235, 255})

	// Draw world
	startRow := max(0, int(g.CameraY/TILE_SIZE))
	endRow := min(ROWS, int((g.CameraY+HEIGHT)/TILE_SIZE+1))
	startCol := max(0, int(g.CameraX/TILE_SIZE))
	endCol := min(COLS, int((g.CameraX+WIDTH)/TILE_SIZE+1))

	for row := startRow; row < endRow; row++ {
		for col := startCol; col < endCol; col++ {
			if g.World[row][col] != nil {
				block := g.World[row][col]
				screenX := float32(col*TILE_SIZE - int(g.CameraX))
				screenY := float32(row*TILE_SIZE - int(g.CameraY))

				// Draw block
				vector.DrawFilledRect(screen, screenX, screenY, TILE_SIZE, TILE_SIZE, BLOCK_TYPES[block.Type].Color, true)
				
				// Draw block value
				text.Draw(screen, strconv.Itoa(block.Value), basicfont.Face7x13, 
					int(screenX)+TILE_SIZE/2-3, int(screenY)+TILE_SIZE/2+3, 
					color.White)
			}
		}
	}

	// Draw player
	vector.DrawFilledRect(screen, 
		float32(g.Player.X-g.CameraX), 
		float32(g.Player.Y-g.CameraY), 
		float32(g.Player.Width), 
		float32(g.Player.Height), 
		color.RGBA{0, 255, 0, 255}, true)

	// Draw UI
	g.drawUI(screen)
}

func (g *Game) drawUI(screen *ebiten.Image) {
	// Draw health bar
	vector.DrawFilledRect(screen, 10, 10, 204, 24, color.RGBA{0, 0, 0, 255}, true)
	vector.DrawFilledRect(screen, 12, 12, float32(200*(g.Player.Health/g.Player.MaxHealth)), 20, 
		color.RGBA{255, 0, 0, 255}, true)

	// Draw inventory
	y := HEIGHT - 60
	for item, count := range g.Player.Inventory {
		text.Draw(screen, fmt.Sprintf("%s:%d", item, count), basicfont.Face7x13, 
			10, int(y), color.White)
		y += 20
	}
}

func (g *Game) Layout(outsideWidth, outsideHeight int) (screenWidth, screenHeight int) {
	return WIDTH, HEIGHT
}

func main() {
	rand.Seed(time.Now().UnixNano())
	ebiten.SetWindowSize(WIDTH, HEIGHT)
	ebiten.SetWindowTitle("Mining Adventure")

	if err := ebiten.RunGame(NewGame()); err != nil {
		fmt.Printf("Game crashed: %v\n", err)
	}
}

// Helper functions
func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min[T float64 | int](a, b T) T {
	if a < b {
		return a
	}
	return b
}
